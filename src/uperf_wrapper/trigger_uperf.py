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

import os
import re
import subprocess
from datetime import datetime
import logging

logger = logging.getLogger("snafu")


class Trigger_uperf():
    def __init__(self, args):
        self.uuid = args.uuid
        self.user = args.user

        self.clientips = args.clientips
        self.remoteip = args.remoteip
        self.hostnetwork = args.hostnetwork
        self.serviceip = args.serviceip
        self.server_node = args.server_node
        self.client_node = args.client_node
        self.cluster_name = args.cluster_name
        self.workload = args.workload
        self.sample = args.sample
        self.resourcetype = args.resourcetype

    def _json_payload(self, data, sample):
        processed = []
        prev_bytes = 0
        prev_ops = 0
        prev_timestamp = 0.0
        for result in data['results']:
            norm_ops = int(result[2]) - prev_ops
            if norm_ops == 0:
                norm_ltcy = 0.0
            else:
                norm_ltcy = ((float(result[0]) - prev_timestamp) / (norm_ops)) * 1000
            processed.append({
                "workload": "uperf",
                "uuid": self.uuid,
                "user": self.user,
                "cluster_name": self.cluster_name,
                "hostnetwork": self.hostnetwork,
                "iteration": sample,
                "remote_ip": self.remoteip,
                "client_ips": self.client_node,
                "uperf_ts": datetime.fromtimestamp(int(result[0].split('.')[0]) / 1000),
                "test_type": data['test'],
                "protocol": data['protocol'],
                "service_ip": self.serviceip,
                "message_size": int(data['message_size']),
                "num_threads": int(data['num_threads']),
                "duration": len(data['results']),
                "bytes": int(result[1]),
                "norm_byte": int(result[1]) - prev_bytes,
                "ops": int(result[2]),
                "norm_ops": norm_ops,
                "norm_ltcy": norm_ltcy,
                "kind": self.resourcetype,
                "client_node": self.client_node,
                "server_node": self.server_node
            })
            prev_timestamp = float(result[0])
            prev_bytes = int(result[1])
            prev_ops = int(result[2])
        return processed

    def _run_uperf(self):
        cmd = "uperf -v -a -R -i 1 -m {}".format(self.workload)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), stderr.strip().decode("utf-8"), process.returncode

    def _parse_stdout(self, stdout):
        # This will effectivly give us:
        # ripsaw-test-stream-udp-16384
        config = re.findall(r"running profile:(.*) \.\.\.", stdout)
        test = re.split("-", config[0])[0]
        protocol = re.split("-", config[0])[1]
        size = re.split("-", config[0])[2]
        nthr = re.split("-", config[0])[3]
        # This will yeild us this structure :
        #     timestamp, number of bytes, number of operations
        # [('1559581000962.0330', '0', '0'), ('1559581001962.8459', '4697358336', '286704') ]
        results = re.findall(r"timestamp_ms:(.*) name:Txn2 nr_bytes:(.*) nr_ops:(.*)", stdout)
        return {"test": test, "protocol": protocol, "message_size": size, "num_threads": nthr,
                "results": results}

    def emit_actions(self):
        if not os.path.exists(self.workload):
            logger.critical("Workload file %s not found" % self.workload)
            exit(1)
        for s in range(1, self.sample + 1):
            logger.info("Starting sample %d out of %d" % (s, self.sample))
            stdout, stderr, rc = self._run_uperf()
            if rc == 1:
                logger.error("UPerf failed to execute, trying one more time..")
                stdout, stderr, rc = self._run_uperf()
                logger.error("stdout: %s" % stdout)
                logger.error("stderr: %s" % stderr)
                if rc == 1:
                    logger.critical("UPerf failed to execute a second time, stopping...")
                    logger.critical("stdout: %s" % stdout)
                    logger.critical("stderr: %s" % stderr)
                    exit(1)
            data = self._parse_stdout(stdout)
            documents = self._json_payload(data, s)
            if len(documents) > 0:
                for document in documents:
                    yield document, 'results'
            logger.info(data)
            logger.info(stdout)
            logger.info("Finished executing sample %d out of %d" % (s, self.sample))
