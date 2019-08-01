#!/usr/bin/env python
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# This wrapper assumes the following in fiojob
# per_job_logs=true
#

import argparse
from datetime import datetime
from copy import deepcopy
from fio_hist_parser import compute_percentiles_from_logs
import re
import os
import sys
import json
import subprocess
import elasticsearch
import numpy as np
import configparser
import statistics
import time

_log_files={'bw':{'metric':'bandwidth'},'iops':{'metric':'iops'},'lat':{'metric':'latency'},'clat':{'metric':'latency'},'slat':{'metric':'latency'}} # ,'clat_hist_processed'
_data_direction={0:'read',1:'write',2:'trim'}


class Fio_Analyzer:
    """
    Fio Analyzer - this class will consume processed fio json results and calculate the average total iops for x number of samples.
    results are analyzed based on operation and io size, this is a static evaluation and future enhancements could evalute results based on
    other properties dynamically.
    """
    def __init__(self, uuid, user):
        self.uuid = uuid
        self.user = user
        self.suffix = "analyzed_result"
        self.fio_processed_results_list = []
        self.sample_list = []
        self.operation_list = []
        self.io_size_list = []
        self.sumdoc = {}

    def add_fio_result_documents(self, document_list, starttime):
        """
        for each new document add it to the results list with its starttime
        """
        for document in document_list:
            fio_result = {}
            fio_result["document"] = document
            fio_result["starttime"] = starttime
            self.fio_processed_results_list.append(fio_result)


    def calculate_iops_sum(self):
        """
        will loop through all documents and will populate parameter lists and sum total iops across all host
        for a specific operation and io size
        """

        for fio_result in self.fio_processed_results_list:
            if fio_result['document']['fio']['jobname'] != 'All clients':
                sample = fio_result['document']['sample']
                bs = fio_result['document']['global_options']['bs']
                rw = fio_result['document']['fio']['job options']['rw']
                
                if sample not in self.sample_list: self.sample_list.append(sample) 
                if rw not in self.operation_list: self.operation_list.append(rw)
                if bs not in self.io_size_list: self.io_size_list.append(bs)

        for sample in self.sample_list:
            self.sumdoc[sample] = {}
            for rw in self.operation_list:
                self.sumdoc[sample][rw] = {}
                for bs in self.io_size_list:
                    self.sumdoc[sample][rw][bs] = {}

            #get measurements

        for fio_result in self.fio_processed_results_list:
            if fio_result['document']['fio']['jobname'] != 'All clients':
                sample = fio_result['document']['sample']
                bs = fio_result['document']['global_options']['bs']
                rw = fio_result['document']['fio']['job options']['rw']

                if not self.sumdoc[sample][rw][bs]:
                    time_s = fio_result['starttime'] / 1000.0
                    self.sumdoc[sample][rw][bs]['date'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(time_s))
                    self.sumdoc[sample][rw][bs]['write'] = 0
                    self.sumdoc[sample][rw][bs]['read'] = 0
                      
                self.sumdoc[sample][rw][bs]['write'] += int(fio_result['document']['fio']["write"]["iops"])
                self.sumdoc[sample][rw][bs]['read'] += int(fio_result['document']['fio']["read"]["iops"])

    def emit_payload(self):
        """
        Will calculate the average iops across multiple samples and return list containing items for each result based on operation/io size 
        """

        importdoc = {"ceph_benchmark_test": {"test_data": {}},
                     "uuid": self.uuid,
                     "user": self.user
                     }

        self.calculate_iops_sum()
        payload_list = []

        for oper in self.operation_list:
            for io_size in self.io_size_list:
                average_write_result_list = []
                average_read_result_list = []
                total_ary = []
                tmp_doc = {}
                tmp_doc['object_size'] = io_size # set document's object size
                tmp_doc['operation'] = oper # set documents operation
                firstrecord = True
                calcuate_percent_std_dev = False

                for itera in self.sample_list: # 
                    average_write_result_list.append(self.sumdoc[itera][oper][io_size]['write'])
                    average_read_result_list.append(self.sumdoc[itera][oper][io_size]['read'])

                    if firstrecord:
                        importdoc['date'] = self.sumdoc[itera][oper][io_size]['date']
                        firstrecord = True

                read_average = (sum(average_read_result_list)/len(average_read_result_list))
                if read_average > 0.0:
                    tmp_doc['read-iops'] = read_average
                    if len(average_read_result_list) > 1:
                        calcuate_percent_std_dev = True
                else:
                    tmp_doc['read-iops'] = 0

                write_average = (sum(average_write_result_list)/len(average_write_result_list))
                if write_average > 0.0:
                    tmp_doc['write-iops'] = write_average
                    if len(average_write_result_list) > 1:
                        calcuate_percent_std_dev = True
                else:
                    tmp_doc['write-iops'] = 0

                tmp_doc['total-iops'] = (tmp_doc['write-iops'] + tmp_doc['read-iops'])

                if calcuate_percent_std_dev:
                    if "read" in oper:
                        tmp_doc['std-dev-%s' % io_size] = round(((statistics.stdev(average_read_result_list) / read_average) * 100), 3)
                    elif "write" in oper:
                        tmp_doc['std-dev-%s' % io_size] = round(((statistics.stdev(average_write_result_list) / write_average) * 100), 3)
                    elif "randrw" in oper:
                        tmp_doc['std-dev-%s' % io_size] = round((((statistics.stdev(average_read_result_list) + statistics.stdev(average_write_result_list)) / tmp_doc['total-iops'])* 100), 3)

                importdoc['ceph_benchmark_test']['test_data'] = tmp_doc
                payload_list.append(importdoc)

        return payload_list


def _document_payload(data, user, uuid, sample, list_hosts, end_time, fio_version, fio_jobs_dict): #pod_details,
    processed = []
    fio_starttime = {}
    earliest_starttime = float('inf')
    for result in data["client_stats"] :
        document = {
          "uuid": uuid,
          "user": user,
          "hosts": list_hosts,
          "fio-version": fio_version,
          "timestamp_end": int(end_time)*1000, #this is in ms
          #"nodeName": pod_details["hostname"],
          "sample": int(sample),
          "fio": result
        }
        if 'global' in fio_jobs_dict.keys():
            document['global_options'] = fio_jobs_dict['global']
        processed.append(document)
        if result['jobname'] != 'All clients':
            start_time= (int(end_time) * 1000) - result['job_runtime']
            fio_starttime[result['hostname']] = start_time
            if start_time < earliest_starttime:
                earliest_starttime = start_time
    return processed, fio_starttime, earliest_starttime

def _log_payload(directory, user, uuid, sample, fio_jobs_dict, fio_version, fio_starttime, list_hosts, job): #pod_details
    logs = []
    _current_log_files = deepcopy(_log_files)
    job_options = fio_jobs_dict[job]
    if 'gtod_reduce' in job_options:
        del _current_log_files['slat']
        del _current_log_files['clat']
        del _current_log_files['bw']
    if 'disable_lat' in job_options:
        del _current_log_files['lat']
    if 'disable_slat' in job_options:
        del _current_log_files['slat']
    if 'disable_clat' in job_options:
        del _current_log_files['clat']
    if 'disable_bw' in job_options or 'disable_bw_measurement' in job_options:
        del _current_log_files['bw']
    for log in _current_log_files.keys():
        for host in list_hosts:
            log_file_prefix_string = 'write_' + str(log) + '_log'
            if log in ['clat','slat']:
                log_file_prefix_string = 'write_lat_log'
            try:
                log_file_name = str(job_options[log_file_prefix_string]) + '_' + str(log) + '.1.log.' + str(host)
            except KeyError:
                try:
                    log_file_name = str(fio_jobs_dict['global'][log_file_prefix_string]) + '_' + str(log) + '.1.log.' + str(host)
                except:
                    print("Error setting log_file_name")
            with open(directory+'/'+str(log_file_name), 'r') as log_file:
                for log_line in log_file:
                    log_line_values = str(log_line).split(", ")
                    if len(log_line_values) == 4:
                        log_dict = {
                          "uuid": uuid,
                          "user": user,
                          "host": host,
                          "fio-version": fio_version,
                          "job_options": job_options,
                          "job_name": str(job),
                          "sample": int(sample),
                          "log_name": str(log),
                          "timestamp": int(fio_starttime[host]) + int(log_line_values[0]), #this is in ms
                          str(_current_log_files[log]['metric']): int(log_line_values[1]),
                          #"nodeName": pod_details["hostname"],
                          "data_direction": _data_direction[int(log_line_values[2])],
                          "offset": int(log_line_values[3])
                        }
                        if 'global' in fio_jobs_dict.keys():
                            log_dict['global_options'] = fio_jobs_dict['global']
                        logs.append(log_dict)
    return logs

def _histogram_payload(processed_histogram_file, user, uuid, sample, fio_jobs_dict, fio_version, longest_fio_startime, list_hosts, job, numjob=1): #pod_details
    logs = []
    with open(processed_histogram_file, 'r') as log_file:
        for log_line in log_file:
            log_line_values = str(log_line).split(", ")
            if len(log_line_values) == 7 and not (any(len(str(x)) <= 0 for x in log_line_values)):
                print(log_line_values)
                log_dict = {
                  "uuid": uuid,
                  "user": user,
                  "hosts": list_hosts,
                  "fio-version": fio_version,
                  "job_options": fio_jobs_dict[job],
                  "job_name": str(job),
                  "sample": int(sample),
                  "log_name": "clat_hist",
                  "timestamp": int(longest_fio_startime) + int(log_line_values[0]), #this is in ms
                  "number_samples_histogram": int(log_line_values[1]),
                  "min": float(log_line_values[2]),
                  "median": float(log_line_values[3]),
                  "p95": float(log_line_values[4]),
                  "p99": float(log_line_values[5]),
                  "max": float(log_line_values[6])
                }
                if 'global' in fio_jobs_dict.keys():
                    log_dict['global_options'] = fio_jobs_dict['global']
                logs.append(log_dict)
    return logs

def _index_result(es,document_index_suffix,payload):
    index = es['index_prefix'] + '-' + str(document_index_suffix)
    es = elasticsearch.Elasticsearch([
        {'host': es['server'],'port': es['port'] }],send_get_body_as='POST')
    indexed=True
    processed_count = 0
    total_count = 0
    for result in payload:
        try:
            es.index(index=index, doc_type="result", body=result)
            processed_count += 1
        except Exception as e:
            print(repr(e) + "occurred for the json document:")
            print(str(result))
            indexed=False
        total_count += 1
    return indexed, processed_count, total_count

def _clean_output(fio_output_file):
    cmd = ["sed", "-i", "/{/,$!d"]
    cmd.append(str(fio_output_file))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return stdout.strip(), process.returncode

def _run_fiod(hosts_file, fiojob_file, output_dir, fio_output_file):
    cmd = ["fio", "--client=", "path_file" ,"--output-format=json", "--output="]
    cmd[1] = "--client=" + str(hosts_file)
    cmd[2] = fiojob_file
    cmd[4] = "--output=" + str(fio_output_file)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=output_dir)
    stdout,stderr = process.communicate()
    return stdout.strip(), process.returncode

def _parse_jobfile(job_path):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read(job_path)
    return config

def _parse_jobs(job_dict, jobs):
    job_dicts = {}
    if 'global' in job_dict.keys():
        job_dicts['global'] = dict(job_dict['global'])
    for job in jobs:
        job_dicts[job] = dict(job_dict[job])
    return job_dicts

def _process_histogram(job_dict, hosts, job, working_dir, processed_histogram_prefix, histogram_output_file, numjob=1):
    histogram_input_file_list = []
    for host in hosts:
        input_file = working_dir + '/' + processed_histogram_prefix + '.' + str(numjob) + '.log.' + str(host)
        histogram_input_file_list.append(input_file)
    print(histogram_input_file_list)
    if 'log_hist_msec' not in job_dict[job].keys():
        if 'global' in job_dict.keys() and 'log_hist_msec' not in job_dict['global'].keys():
            print("log_hist_msec, so can't process histogram logs")
            exit(1)
        else:
            _log_hist_msec = job_dict['global']['log_hist_msec']
    else:
        _log_hist_msec = job_dict[job]['log_hist_msec']
    compute_percentiles_from_logs(output_csv_file=histogram_output_file,file_list=histogram_input_file_list,log_hist_msec=_log_hist_msec)

def _build_fio_job(job_name, job_dict, parent_dir, fio_job_file_name):
    config = configparser.ConfigParser()
    if 'global' in job_dict.keys():
        config['global'] = job_dict['global']
    config[job_name] = job_dict[job_name]
    if os.path.exists(fio_job_file_name):
        os.remove(fio_job_file_name)
        print("file " + fio_job_file_name + " already exists. overwriting")
    with open(fio_job_file_name, 'w') as configfile:
        config.write(configfile, space_around_delimiters=False)

def _trigger_fio(fio_jobs, working_dir, fio_jobs_dict, host_file, user, uuid, sample, fio_analyzer_obj, es, indexed=False, numjob=1):
    with open(host_file) as f:
        hosts = f.read().splitlines()
    for job in fio_jobs:
        job_dir = working_dir + '/' + str(job)
        if not os.path.exists(job_dir):
            os.mkdir(job_dir)
        fio_output_file = job_dir + '/' + str('fio-result.json')
        fio_job_file = job_dir + '/fiojob'
        _build_fio_job(job, fio_jobs_dict, job_dir, fio_job_file)
        stdout = _run_fiod(host_file, fio_job_file, job_dir, fio_output_file)
        if stdout[1] != 0:
            print("Fio failed to execute, trying one more time..")
            stdout = _run_fiod(host_file, fio_job_file, job_dir, fio_output_file)
            if stdout[1] != 0:
                print("Fio failed to execute a second time, stopping...")
                exit(1)
        clean_stdout = _clean_output(fio_output_file)
        if clean_stdout[1] != 0:
            print("failed to parse the output file")
            exit(1)
        print("fio has successfully finished sample {} executing for jobname {} and results are in the dir {}\n".format(sample, job, job_dir))
        if indexed:
            with open(fio_output_file) as f:
                data = json.load(f)
            fio_endtime = int(data['timestamp']) # in epoch seconds
            fio_version = data["fio version"]
            fio_result_documents, fio_starttime, earliest_starttime = _document_payload(data, user, uuid, sample, hosts, fio_endtime, fio_version, fio_jobs_dict) #hosts_metadata
            # Add fio result document to fio analyzer object
            fio_analyzer_obj.add_fio_result_documents(fio_result_documents, earliest_starttime)
            if indexed:
                if len(fio_result_documents) > 0:
                    _status_results, processed_count, total_count = _index_result(es, 'results', fio_result_documents)
                    if _status_results:
                        print("Succesfully indexed " + str(total_count) + " fio result documents to index {}".format(str(es['index_prefix'])+'-results'))
                    else:
                        print(str(processed_count) + "/" + str(total_count) + "succesfully indexed")
            try:
                if fio_jobs_dict[job]['filename_format'] != 'f.\$jobnum.\$filenum' or int(fio_jobs_dict[job]['numjobs']) != 1:
                    print("filename_format is not 'f.\$jobnum.\$filenum' and/or numjobs is not 1, so can't process logs")
                    exit(1)
            except KeyError:
                try:
                    if fio_jobs_dict['global']['filename_format'] != 'f.\$jobnum.\$filenum' or int(fio_jobs_dict['global']['numjobs']) != 1:
                        print("filename_format is not 'f.\$jobnum.\$filenum' and/or numjobs is not 1, so can't process logs")
                        exit(1)
                except:
                    print("Error getting filename_format")
            fio_log_documents = _log_payload(job_dir, user, uuid, sample, fio_jobs_dict, fio_version, fio_starttime, hosts, job)
            if indexed:
                if len(fio_log_documents) > 0:
                    _status_results, processed_count, total_count = _index_result(es, 'logs', fio_log_documents)
                    if _status_results:
                        print("Succesfully indexed " + str(total_count) + " fio logs to index {}".format(str(es['index_prefix'])+'-logs'))
                    else:
                        print(str(processed_count) + "/" + str(total_count) + "succesfully indexed")
            try:
                processed_histogram_prefix = fio_jobs_dict[job]['write_hist_log'] +'_clat_hist'
            except KeyError:
                try:
                    processed_histogram_prefix = fio_jobs_dict['global']['write_hist_log'] +'_clat_hist'
                except:
                    print("Error setting processed_histogram_prefix")
            histogram_output_file = job_dir + '/' + processed_histogram_prefix + '_processed.' + str(numjob)
            _process_histogram(fio_jobs_dict, hosts, job, job_dir, processed_histogram_prefix, histogram_output_file)
            histogram_documents = _histogram_payload(histogram_output_file, user, uuid, sample, fio_jobs_dict, fio_version, earliest_starttime, hosts, job)
            if indexed:
                if len(histogram_documents) > 0:
                    _status_results, processed_count, total_count =_index_result(es, 'logs', histogram_documents)
                    if _status_results:
                        print("Succesfully indexed " + str(total_count) + " processed histogram logs to index {}".format(str(es['index_prefix'])+'-logs'))
                    else:
                        print(str(processed_count) + "/" + str(total_count) + "succesfully indexed")
        else:
            print("Not indexing\n")


def main():
    parser = argparse.ArgumentParser(description="fio-d Wrapper script")
    parser.add_argument(
        'hosts', help='Provide host file location')
    parser.add_argument(
        'job', help='path to job file')
    parser.add_argument(
        '-s', '--sample', type=int, default=1, help='number of times to run benchmark, defaults to 1')
    parser.add_argument(
        '-d', '--dir', help='output parent directory', default=os.path.dirname(os.getcwd()))
    args = parser.parse_args()

    uuid = ""
    user = ""
    server = ""
    es={}
    index_results = False
    if "es" in os.environ:
        es['server'] = os.environ["es"]
        es['port'] = os.environ["es_port"]
        es['index_prefix'] = os.environ["es_index"]
        index_results = True
    if "uuid" in os.environ:
        uuid = os.environ["uuid"]
    if "test_user" in os.environ:
        user = os.environ["test_user"]
    # if "pod_details" in os.environ:
    #     hosts_metadata = os.environ["pod_details"]
    sample = args.sample
    working_dir = args.dir
    host_file_path = args.hosts
    _fio_job_dict = _parse_jobfile(args.job)
    fio_job_names = _fio_job_dict.sections()
    if 'global' in fio_job_names:
        fio_job_names.remove('global')
    fio_jobs_dict = _parse_jobs(_fio_job_dict, fio_job_names)
    fio_analyzer_obj = Fio_Analyzer(uuid, user)
    for i in range(1, sample + 1):
        sample_dir = working_dir + '/' + str(i)
        if not os.path.exists(sample_dir):
            os.mkdir(sample_dir)
        _trigger_fio(fio_job_names, sample_dir, fio_jobs_dict, host_file_path, user, uuid, i, fio_analyzer_obj, es, index_results)
    if index_results:
        _index_result(es, fio_analyzer_obj.suffix, fio_analyzer_obj.emit_payload())

if __name__ == '__main__':
    sys.exit(main())
