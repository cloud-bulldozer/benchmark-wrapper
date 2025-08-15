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

import datetime
import logging
import os
import re
import subprocess

logger = logging.getLogger("snafu")


class Trigger_oslat:
    def __init__(self, args):
        self.uuid = args.uuid
        self.user = args.user
        self.path = args.path
        self.samples = args.samples

        self.duration = args.duration
        self.disable_cpu_balance = args.disable_cpu_balance
        self.use_taskset = args.use_taskset
        self.cluster_name = args.cluster_name

    def _parse_stdout(self, stdout):
        allowed_cpus_list = re.search(r"allowed.+", stdout).group().split(":")[1].strip()
        cpus_list = re.search(r"CPU list.+", stdout).group().split(":")[1].strip()
        cpu_main_thread = re.search(r"main thread.+", stdout).group().split(":")[1].strip()
        command = re.search(r"cmd to.+", stdout).group().split(":")[1].strip()
        avg_latencies = [
            float(i)
            for i in re.search(r"Average.+", stdout).group().split(":")[1].split("(")[0].strip().split()
        ]
        max_latencies = [
            int(i)
            for i in re.search(r"Maximum.+", stdout).group().split(":")[1].split("(")[0].strip().split()
        ]
        min_latencies = [
            int(i)
            for i in re.search(r"Minimum.+", stdout).group().split(":")[1].split("(")[0].strip().split()
        ]
        result = {
            "allowed_cpus_list": allowed_cpus_list,
            "cpus_list": cpus_list,
            "cpu_main_thread": cpu_main_thread,
            "command": command,
            "avg_latencies": avg_latencies,
            "max_latencies": max_latencies,
            "min_latencies": min_latencies,
        }
        return result

    def _json_payload(self, data, sample, timestamp):
        payload = {
            "uuid": self.uuid,
            "user": self.user,
            "timestamp": timestamp,
            "use_taskset": self.use_taskset,
            "duration": self.duration,
            "disable_cpu_balance": self.disable_cpu_balance,
            "sample": sample,
            "cluster_name": self.cluster_name,
            "allowed_cpus_list": data["allowed_cpus_list"],
            "cpus_list": data["cpus_list"],
            "cpu_main_thread": data["cpu_main_thread"],
            "command": data["command"],
            "avg_latencies": data["avg_latencies"],
            "max_latencies": data["max_latencies"],
            "min_latencies": data["min_latencies"],
        }
        return payload

    def _run_oslat(self):
        cmd = f"dumb-init -- {self.path}"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logger.info("Raw result is \n{}".format(stdout.strip().decode("utf-8")))
        return stdout.strip().decode("utf-8"), stderr.strip().decode("utf-8"), process.returncode

    def emit_actions(self):
        if not os.path.exists(self.path):
            logger.critical(f"oslat script {self.path} not found")
            exit(1)
        for s in range(1, self.samples + 1):
            logger.info(f"Starting sample {s} out of {self.samples}")
            logger.info("Starting oslat benchmark")
            stdout, stderr, rc = self._run_oslat()
            timestamp = datetime.datetime.now()
            if rc == 0:
                logger.info("Starting output parsing")
                data = self._parse_stdout(stdout)
                document = self._json_payload(data, s, timestamp)
                yield document, "results"
            else:
                raise Exception("Failed to produce oslat results document")
                exit(1)
