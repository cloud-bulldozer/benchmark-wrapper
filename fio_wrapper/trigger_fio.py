import configparser
import json
import logging
import os
import subprocess
from copy import deepcopy
from datetime import datetime

from fio_wrapper.fio_hist_parser import compute_percentiles_from_logs

logger = logging.getLogger("snafu")

_log_files = {'bw': {'metric': 'bandwidth'},
              'iops': {'metric': 'iops'},
              'lat': {'metric': 'latency'},
              'clat': {'metric': 'latency'},
              'slat': {'metric': 'latency'}}  # ,'clat_hist_processed'
_data_direction = {0: 'read', 1: 'write', 2: 'trim'}


class _trigger_fio:
    """
        Will execute fio with the provided arguments and return normalized results for indexing
    """

    def __init__(self, fio_jobs, cluster_name, working_dir, fio_jobs_dict, host_file, user, uuid,
                 sample, fio_analyzer_obj, numjob=1, process_histogram=False):
        self.fio_jobs = fio_jobs
        self.working_dir = working_dir
        self.fio_jobs_dict = fio_jobs_dict
        self.host_file = host_file
        self.user = user
        self.uuid = uuid
        self.sample = sample
        self.fio_analyzer_obj = fio_analyzer_obj
        self.numjob = numjob
        self.histogram_process = process_histogram
        self.cluster_name = cluster_name

    def _document_payload(self,
                          data,
                          user, uuid, sample,
                          list_hosts, end_time,
                          fio_version, fio_jobs_dict):  # pod_details,
        processed = []
        fio_starttime = {}
        earliest_starttime = float('inf')
        for result in data["client_stats"]:
            document = {
                "uuid": uuid,
                "user": user,
                "cluster_name": self.cluster_name,
                "hosts": list_hosts,
                "fio-version": fio_version,
                "timestamp_end": int(end_time) * 1000,  # this is in ms
                # "nodeName": pod_details["hostname"],
                "sample": int(sample),
                "fio": result
            }
            if 'global' in fio_jobs_dict.keys():
                document['global_options'] = fio_jobs_dict['global']
            processed.append(document)
            if result['jobname'] != 'All clients':

                ramp_time = 0
                if 'ramp_time' in result['job options']:
                    ramp_time = int(result['job options']['ramp_time'])
                elif 'ramp_time' in document['global_options']:
                    ramp_time = int(document['global_options']['ramp_time'])

                # set start time from s to ms
                start_time = (int(end_time) * 1000)
                logging_start_time = start_time

                if ramp_time > 0:
                    # set logging start time by adding ramp time to start time (in ms)
                    logging_start_time = start_time + (ramp_time * 1000)

                # The only external method that uses fio_starttime is _log_payload,
                # so we can set time to logging_start_time
                fio_starttime[result['hostname']] = logging_start_time

                if start_time < earliest_starttime:
                    earliest_starttime = start_time

        return processed, fio_starttime, earliest_starttime

    def _log_payload(self, directory, user, uuid, sample, fio_jobs_dict, fio_version,
                     fio_starttime, list_hosts, job):  # pod_details
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
        # find the number of jobs either in the job options or global options
        if 'numjobs' in job_options:
            numjob_list = job_options['numjobs']
        else:
            numjob_list = fio_jobs_dict['global']['numjobs']

        for log in _current_log_files.keys():
            for host in list_hosts:
                for numjob in range(int(numjob_list)):
                    numjob = numjob + 1
                    log_file_prefix_string = 'write_' + str(log) + '_log'
                    if log in ['clat', 'slat']:
                        log_file_prefix_string = 'write_lat_log'
                    try:
                        log_file_name = str(job_options[log_file_prefix_string]) + '_' \
                            + str(log) + '.' + str(numjob) + '.log.' + str(host)
                    except KeyError:
                        try:
                            log_file_name = str(fio_jobs_dict['global'][log_file_prefix_string]) \
                                + '_' + str(log) + '.' + str(numjob) + '.log.' + str(host)

                        except:  # noqa
                            logger.info("Error setting log_file_name")
                    with open(directory + '/' + str(log_file_name), 'r') as log_file:
                        for log_line in log_file:
                            log_line_values = str(log_line).split(", ")
                            if len(log_line_values) == 5:
                                timestamp_ms = int(fio_starttime[host]) + int(log_line_values[0])
                                newtime = datetime.fromtimestamp(timestamp_ms / 1000.0)
                                log_dict = {
                                    "uuid": uuid,
                                    "user": user,
                                    "host": host,
                                    "cluster_name": self.cluster_name,
                                    "job_number": numjob,
                                    "fio-version": fio_version,
                                    "job_options": job_options,
                                    "job_name": str(job),
                                    "log_file": log_file_name,
                                    "sample": int(sample),
                                    "log_name": str(log),
                                    "timestamp": timestamp_ms,  # this is in ms
                                    "date": newtime.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                    str(_current_log_files[log]['metric']): int
                                    (log_line_values[1]),
                                    # "nodeName": pod_details["hostname"],
                                    "data_direction": _data_direction[int(log_line_values[2])],
                                    "block_size": int(log_line_values[3]),
                                    "offset": int(log_line_values[4])
                                }
                                if 'global' in fio_jobs_dict.keys():
                                    log_dict['global_options'] = fio_jobs_dict['global']
                                logs.append(log_dict)
        return logs

    def _histogram_payload(self, processed_histogram_file, user, uuid, sample, fio_jobs_dict,
                           fio_version, longest_fio_startime, list_hosts, job,
                           numjob=1):  # pod_details
        logs = []
        with open(processed_histogram_file, 'r') as log_file:
            for log_line in log_file:
                log_line_values = str(log_line).split(", ")
                if len(log_line_values) == 7 and not \
                        (any(len(str(x)) <= 0 for x in log_line_values)):
                    logger.debug(log_line_values)
                    timestamp_ms = int(longest_fio_startime) + int(log_line_values[0])
                    newtime = datetime.fromtimestamp(timestamp_ms / 1000.0)
                    log_dict = {
                        "uuid": uuid,
                        "user": user,
                        "hosts": list_hosts,
                        "cluster_name": self.cluster_name,
                        "fio-version": fio_version,
                        "job_options": fio_jobs_dict[job],
                        "job_name": str(job),
                        "sample": int(sample),
                        "log_name": "clat_hist",
                        "timestamp": timestamp_ms,  # this is in ms
                        "date": newtime.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
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

    def _clean_output(self, fio_output_file):
        cmd = ["sed", "-i", "/{/,$!d"]
        cmd.append(str(fio_output_file))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip(), process.returncode

    def _run_fiod(self, hosts_file, fiojob_file, output_dir, fio_output_file):
        cmd = ["fio", "--client=", "path_file", "--output-format=json", "--output="]
        cmd[1] = "--client=" + str(hosts_file)
        cmd[2] = fiojob_file
        cmd[4] = "--output=" + str(fio_output_file)
        # logger.debug(cmd)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=output_dir)
        stdout, stderr = process.communicate()
        return stdout.strip(), process.returncode

    def _process_histogram(self, job_dict, hosts, job, working_dir, processed_histogram_prefix,
                           histogram_output_file, numjob=1):
        histogram_input_file_list = []
        for host in hosts:
            input_file = working_dir + '/' + processed_histogram_prefix + '.' + str(
                numjob) + '.log.' + str(host)
            histogram_input_file_list.append(input_file)
        logger.debug(histogram_input_file_list)
        if 'log_hist_msec' not in job_dict[job].keys():
            if 'global' in job_dict.keys() and 'log_hist_msec' not in job_dict['global'].keys():
                logger.info("log_hist_msec not found, so can't process histogram logs")
                exit(1)
            else:
                _log_hist_msec = job_dict['global']['log_hist_msec']
        else:
            _log_hist_msec = job_dict[job]['log_hist_msec']
        compute_percentiles_from_logs(output_csv_file=histogram_output_file,
                                      file_list=histogram_input_file_list,
                                      log_hist_msec=_log_hist_msec)

    def _build_fio_job(self, job_name, job_dict, parent_dir, fio_job_file_name):
        config = configparser.ConfigParser()
        if 'global' in job_dict.keys():
            config['global'] = job_dict['global']
        config[job_name] = job_dict[job_name]
        if os.path.exists(fio_job_file_name):
            os.remove(fio_job_file_name)
            logger.info("file " + fio_job_file_name + " already exists. overwriting")
        with open(fio_job_file_name, 'w') as configfile:
            config.write(configfile, space_around_delimiters=False)

    def emit_actions(self):
        """
        Executes fio test and calls document parsers, if index_data is true will yield
        normalized data
        """

        # access user specified host file
        with open(self.host_file) as f:
            hosts = f.read().splitlines()

        # execute for each job in the user specified job file
        for job in self.fio_jobs:

            job_dir = self.working_dir + '/' + str(job)
            if not os.path.exists(job_dir):
                os.mkdir(job_dir)
            fio_output_file = job_dir + '/' + str('fio-result.json')
            fio_job_file = job_dir + '/fiojob'

            self._build_fio_job(job, self.fio_jobs_dict, job_dir, fio_job_file)

            stdout = self._run_fiod(self.host_file, fio_job_file, job_dir, fio_output_file)
            if stdout[1] != 0:
                logger.error("Fio failed to execute, trying one more time..")
                stdout = self._run_fiod(self.host_file, fio_job_file, job_dir, fio_output_file)
                if stdout[1] != 0:
                    logger.error("Fio failed to execute a second time, stopping...")
                    logger.error(stdout)
                    exit(1)
            clean_stdout = self._clean_output(fio_output_file)

            if clean_stdout[1] != 0:
                logger.error("failed to parse the output file")
                exit(1)
            logger.info(
                "fio has successfully finished sample {} executing for jobname {} and results "
                "are in the dir {}\n".format(
                    self.sample, job, job_dir))

            with open(fio_output_file) as f:
                data = json.load(f)
            fio_endtime = int(data['timestamp'])  # in epoch seconds
            fio_version = data["fio version"]

            # parse fio json file, return list of normalized documents and structured start times
            fio_result_documents, fio_starttime, earliest_starttime = self._document_payload(
                data, self.user, self.uuid, self.sample, hosts, fio_endtime, fio_version,
                self.fio_jobs_dict)  # hosts_metadata

            # Add fio result document to fio analyzer object
            self.fio_analyzer_obj.add_fio_result_documents(fio_result_documents,
                                                           earliest_starttime)

            # from the returned normalized fio json document yield up for indexing
            index = "results"
            for document in fio_result_documents:
                yield document, index

            # check to determine if logs can be parsed, if not fail
            try:
                if self.fio_jobs_dict[job]['filename_format'] != 'f.\$jobnum.\$filenum':  # noqa
                    logger.error("filename_format is not 'f.\$jobnum.\$filenum'")  # noqa
                    exit(1)
            except KeyError:
                try:
                    if self.fio_jobs_dict['global']['filename_format'] != 'f.\$jobnum.\$filenum':  # noqa
                        logger.error("filename_format is not 'f.\$jobnum.\$filenum'")  # noqa
                        exit(1)
                except:  # noqa
                    logger.error("Error getting filename_format")

            # parse all fio log files, return list of normalized log documents
            fio_log_documents = self._log_payload(job_dir, self.user, self.uuid, self.sample,
                                                  self.fio_jobs_dict,
                                                  fio_version,
                                                  fio_starttime,
                                                  hosts, job)

            # if indexing is turned on yield back normalized data
            index = "log"
            for document in fio_log_documents:
                yield document, index
            if self.histogram_process:
                try:
                    processed_histogram_prefix = self.fio_jobs_dict[job]['write_hist_log'] + '_clat_hist'
                except KeyError:
                    try:
                        processed_histogram_prefix = self.fio_jobs_dict['global']['write_hist_log'] +\
                            '_clat_hist'
                    except:  # noqa
                        logger.error("Error setting processed_histogram_prefix")
                histogram_output_file = job_dir + \
                    '/' + processed_histogram_prefix + '_processed.' + str(self.numjob)
                self._process_histogram(self.fio_jobs_dict, hosts, job, job_dir,
                                        processed_histogram_prefix, histogram_output_file)
                histogram_documents = self._histogram_payload(histogram_output_file, self.user,
                                                              self.uuid, self.sample,
                                                              self.fio_jobs_dict, fio_version,
                                                              earliest_starttime, hosts, job)
                # if indexing is turned on yield back normalized data

                index = "hist-log"
                for document in histogram_documents:
                    yield document, index
