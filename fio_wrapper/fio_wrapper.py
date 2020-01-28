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

import configparser
import logging
# This wrapper assumes the following in fiojob
# per_job_logs=true
#
import os

import requests

from fio_wrapper import trigger_fio
from fio_wrapper.fio_analyzer import Fio_Analyzer

logger = logging.getLogger("snafu")


class fio_wrapper():

    def __init__(self, parser):
        # collect arguments

        # parser = argparse.ArgumentParser(description="fio-d Wrapper script")
        parser.add_argument(
            '-H', '--hosts', help='Provide host file location')
        parser.add_argument(
            '-j', '--job', help='path to job file')
        parser.add_argument(
            '-s', '--sample', type=int, default=1,
            help='number of times to run benchmark, defaults to 1')
        parser.add_argument(
            '-d', '--dir', help='output parent directory', default=os.path.dirname(os.getcwd()))
        parser.add_argument(
            '-hp', '--histogramprocess', help='Process and index histogram results',
            default=False)
        self.args = parser.parse_args()

        self.args.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.args.cluster_name = os.environ["clustername"]

        self.uuid = ""
        self.user = ""
        self.server = ""
        self.cache_drop_ip = ""

        if "uuid" in os.environ:
            self.uuid = os.environ["uuid"]
        if "test_user" in os.environ:
            self.user = os.environ["test_user"]
        if "ceph_cache_drop_pod_ip" in os.environ:
            self.cache_drop_ip = os.environ["ceph_cache_drop_pod_ip"]
        # if "pod_details" in os.environ:
        #     hosts_metadata = os.environ["pod_details"]
        self.sample = self.args.sample
        self.working_dir = self.args.dir
        self.host_file_path = self.args.hosts
        self._fio_job_dict = self._parse_jobfile(self.args.job)
        self.fio_job_names = self._fio_job_dict.sections()
        if 'global' in self.fio_job_names:
            self.fio_job_names.remove('global')
        self.fio_jobs_dict = self._parse_jobs(self._fio_job_dict, self.fio_job_names)

    def run(self):
        fio_analyzer_obj = Fio_Analyzer(self.uuid, self.user, self.args.cluster_name)
        # execute fio for X number of samples, yield the trigger_fio_generator
        for i in range(1, self.sample + 1):
            sample_dir = self.working_dir + '/' + str(i)
            if not os.path.exists(sample_dir):
                os.mkdir(sample_dir)
            if self.cache_drop_ip:
                try:
                    drop = requests.get(
                        "http://{}:9432/drop_osd_caches".format(self.cache_drop_ip)).text
                except:
                    logger.error("Failed HTTP request to Ceph OSD cache drop pod {}".format(
                        self.cache_drop_ip))
                if "SUCCESS" in drop:
                    logger.info("Ceph OSD cache successfully dropped")
                else:
                    logger.error("Request to drop Ceph OSD cache failed")
            trigger_fio_generator = trigger_fio._trigger_fio(self.fio_job_names,
                                                             self.args.cluster_name,
                                                             sample_dir,
                                                             self.fio_jobs_dict,
                                                             self.host_file_path,
                                                             self.user,
                                                             self.uuid,
                                                             i,
                                                             fio_analyzer_obj,
                                                             self.args.histogramprocess)
            yield trigger_fio_generator

        yield fio_analyzer_obj

    def _parse_jobs(self, job_dict, jobs):
        job_dicts = {}
        if 'global' in job_dict.keys():
            job_dicts['global'] = dict(job_dict['global'])
        for job in jobs:
            job_dicts[job] = dict(job_dict[job])
        return job_dicts

    def _parse_jobfile(self, job_path):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(job_path)
        return config
