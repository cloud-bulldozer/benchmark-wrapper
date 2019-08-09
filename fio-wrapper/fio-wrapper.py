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
import os
import sys
# in order to run need to add parent dir to sys.path
parent_dir = os.path.abspath(os.path.join(__file__ ,"../.."))
sys.path.append(parent_dir)

import argparse
import configparser
import elasticsearch
import time, datetime
import logging
import hashlib
import json
from copy import deepcopy
from fio_analyzer import Fio_Analyzer
from utils.py_es_bulk import streaming_bulk
from utils.common_logging import setup_loggers
import trigger_fio

logger = logging.getLogger("fio_wrapper")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

setup_loggers("fio_wrapper", logging.DEBUG)


def main():

    #collect arguments
    parser = argparse.ArgumentParser(description="fio-d Wrapper script")
    parser.add_argument(
        'hosts', help='Provide host file location')
    parser.add_argument(
        'job', help='path to job file')
    parser.add_argument(
        '-s', '--sample', type=int, default=1, help='number of times to run benchmark, defaults to 1')
    parser.add_argument(
        '-d', '--dir', help='output parent directory', default=os.path.dirname(os.getcwd()))
    parser.add_argument(
        '-hp', '--histogramprocess', help='Process and index histogram results', default=False)
    args = parser.parse_args()

    args.index_results = False
    args.prefix = "ripsaw-fio-"
    es={}
    if "es" in os.environ:
        es['server'] = os.environ["es"]
        es['port'] = os.environ["es_port"]
        args.prefix = os.environ["es_index"]
        args.index_results = True

        es = elasticsearch.Elasticsearch([
        {'host': es['server'],'port': es['port'] }],send_get_body_as='POST')

    #call py es bulk using a process generator to feed it ES documents
    res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = streaming_bulk(es, process_generator(args))

    # set up a standard format for time
    FMT = '%Y-%m-%dT%H:%M:%SGMT'
    start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', time.gmtime(res_beg))
    end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', time.gmtime(res_end))
    start_t = datetime.datetime.strptime(start_t, FMT)
    end_t = datetime.datetime.strptime(end_t, FMT)

    #get time delta for indexing run
    tdelta = end_t - start_t
    logger.info("Duration of indexing - %s" % tdelta)
    logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc,
                                                                                                res_dup,
                                                                                                res_fail,
                                                                                                res_retry))

def process_generator(args):

    object_generator = process_data(args)

    for object in object_generator:
        for action, index in object.emit_actions():

            es_valid_document = { "_index": index,
                                  "_type": "_doc",
                                  "_op_type": "create",
                                  "_source": action,
                                  "_id": "" }
            es_valid_document["_id"] = hashlib.md5(str(action).encode()).hexdigest()
            #logger.debug(json.dumps(es_valid_document, indent=4))
            yield es_valid_document

def process_data(args):
    uuid = ""
    user = ""
    server = ""

    index_results = args.index_results

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
    document_index_prefix = args.prefix

    fio_analyzer_obj = Fio_Analyzer(uuid, user, document_index_prefix)
    #execute fio for X number of samples, yield the trigger_fio_generator
    for i in range(1, sample + 1):
        sample_dir = working_dir + '/' + str(i)
        if not os.path.exists(sample_dir):
            os.mkdir(sample_dir)
        trigger_fio_generator = trigger_fio._trigger_fio(fio_job_names,
                                                         sample_dir,
                                                         fio_jobs_dict,
                                                         host_file_path,
                                                         user,
                                                         uuid,
                                                         i,
                                                         fio_analyzer_obj,
                                                         document_index_prefix,
                                                         index_results,
                                                         args.histogramprocess)
        yield trigger_fio_generator

    yield fio_analyzer_obj

def _parse_jobs(job_dict, jobs):
    job_dicts = {}
    if 'global' in job_dict.keys():
        job_dicts['global'] = dict(job_dict['global'])
    for job in jobs:
        job_dicts[job] = dict(job_dict[job])
    return job_dicts

def _parse_jobfile(job_path):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read(job_path)
    return config

if __name__ == '__main__':
    sys.exit(main())
