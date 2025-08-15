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

import argparse
import configparser
import logging
import os

import requests

from . import trigger_fio
from .fio_analyzer import Fio_Analyzer

logger = logging.getLogger("snafu")


class fio_wrapper:
    def __init__(self, parent_parser):
        # collect arguments

        parser_object = argparse.ArgumentParser(
            description="fio-d Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("Fio benchmark")
        parser.add_argument("-H", "--hosts", help="Provide host file location", required=True)
        parser.add_argument("-j", "--job", help="path to job file", required=True)
        parser.add_argument(
            "-s", "--sample", type=int, default=1, help="number of times to run benchmark, defaults to 1"
        )
        parser.add_argument(
            "-d", "--dir", help="output parent directory", default=os.path.dirname(os.getcwd())
        )
        parser.add_argument(
            "-hp", "--histogramprocess", help="Process and index histogram results", default=False
        )
        self.args = parser_object.parse_args()

        self.args.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.args.cluster_name = os.environ["clustername"]

        self.uuid = os.getenv("uuid", "")
        self.user = os.getenv("test_user", "")
        self.cache_drop_ip = os.getenv("ceph_cache_drop_pod_ip", "")
        self.sample = self.args.sample
        self.working_dir = self.args.dir
        self.host_file_path = self.args.hosts
        self._fio_job_dict = self._parse_jobfile(self.args.job)
        self.fio_job_names = self._fio_job_dict.sections()
        if "global" in self.fio_job_names:
            self.fio_job_names.remove("global")
        self.fio_jobs_dict = self._parse_jobs()

    def run(self):
        fio_analyzer_obj = Fio_Analyzer(self.uuid, self.user, self.args.cluster_name)
        # execute fio for X number of samples, yield the trigger_fio_generator
        for i in range(1, self.sample + 1):
            sample_dir = os.path.join(self.working_dir, str(i))
            os.makedirs(sample_dir, exist_ok=True)
            if self.cache_drop_ip:
                try:
                    drop = requests.get(f"http://{self.cache_drop_ip}:9432/drop_osd_caches").text
                except:  # noqa
                    logger.error(f"Failed HTTP request to Ceph OSD cache drop pod {self.cache_drop_ip}")
                if "SUCCESS" in drop:
                    logger.info("Ceph OSD cache successfully dropped")
                else:
                    logger.error("Request to drop Ceph OSD cache failed")
            trigger_fio_generator = trigger_fio._trigger_fio(
                self.fio_job_names,
                self.args.cluster_name,
                sample_dir,
                self.fio_jobs_dict,
                self.host_file_path,
                self.user,
                self.uuid,
                i,
                fio_analyzer_obj,
                self.args.histogramprocess,
            )
            yield trigger_fio_generator

        yield fio_analyzer_obj

    def _parse_jobs(self):
        job_dicts = {}
        if "global" in self._fio_job_dict.keys():
            job_dicts["global"] = dict(self._fio_job_dict["global"])
        for job in self.fio_job_names:
            job_dicts[job] = dict(self._fio_job_dict[job])
        return job_dicts

    def _parse_jobfile(self, job_path):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(job_path)
        return config
