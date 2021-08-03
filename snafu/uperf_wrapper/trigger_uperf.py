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


class Trigger_uperf:
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
        self.num_pairs = args.num_pairs
        self.multus_client = args.multus_client
        self.networkpolicy = args.networkpolicy
        self.nodes_in_iter = args.nodes_in_iter
        self.pod_density = args.pod_density
        self.colocate = args.colocate
        self.step_size = args.step_size
        self.density_range = args.density_range
        self.node_range = args.node_range
        self.pod_id = args.pod_id

    def _json_payload(self, results, data, sample):
        processed = []
        prev_bytes = 0
        prev_ops = 0
        prev_timestamp = 0.0
        for result in results:
            norm_ops = int(result[2]) - prev_ops
            if norm_ops == 0:
                norm_ltcy = 0.0
            else:
                norm_ltcy = ((float(result[0]) - prev_timestamp) / (norm_ops)) * 1000
            datapoint = {
                "workload": "uperf",
                "uuid": self.uuid,
                "user": self.user,
                "cluster_name": self.cluster_name,
                "hostnetwork": self.hostnetwork,
                "iteration": sample,
                "remote_ip": self.remoteip,
                "client_ips": self.clientips,
                "uperf_ts": datetime.fromtimestamp(int(result[0].split(".")[0]) / 1000),
                "service_ip": self.serviceip,
                "bytes": int(result[1]),
                "norm_byte": int(result[1]) - prev_bytes,
                "ops": int(result[2]),
                "norm_ops": norm_ops,
                "norm_ltcy": norm_ltcy,
                "kind": self.resourcetype,
                "client_node": self.client_node,
                "server_node": self.server_node,
                "num_pairs": self.num_pairs,
                "multus_client": self.multus_client,
                "networkpolicy": self.networkpolicy,
                "density": self.pod_density,
                "nodes_in_iter": self.nodes_in_iter,
                "step_size": self.step_size,
                "colocate": self.colocate,
                "density_range": [int(x) for x in self.density_range.split("-") if x != ""],
                "node_range": [int(x) for x in self.node_range.split("-") if x != ""],
                "pod_id": self.pod_id,
            }
            datapoint.update(data)
            processed.append(datapoint)
            prev_timestamp = float(result[0])
            prev_bytes = int(result[1])
            prev_ops = int(result[2])
        return processed

    def _run_uperf(self):
        # short to long cli option for uperf:
        # verbose, all stats, raw output in ms, throughput collection interval is 1 second
        cmd = "uperf -v -a -R -i 1 -m {}".format(self.workload)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), stderr.strip().decode("utf-8"), process.returncode

    def _parse_stdout(self, stdout):
        # This will effectivly give us:
        # <profile name="{{test}}-{{proto}}-{{wsize}}-{{rsize}}-{{nthr}}">
        config = re.findall(r"running profile:(.*) \.\.\.", stdout)[0]
        test_type, protocol, wsize, rsize, nthr = config.split("-")
        # This will yeild us this structure :
        #     timestamp, number of bytes, number of operations
        # [('1559581000962.0330', '0', '0'), ('1559581001962.8459', '4697358336', '286704') ]
        if test_type == "connect":
            results = re.findall(r"timestamp_ms:(.*) name:Txn1 nr_bytes:(.*) nr_ops:(.*)", stdout)
        else:
            results = re.findall(r"timestamp_ms:(.*) name:Txn2 nr_bytes:(.*) nr_ops:(.*)", stdout)
        # We assume message_size=write_message_size to prevent breaking dependant implementations
        return (
            results,
            {
                "test_type": test_type,
                "protocol": protocol,
                "message_size": int(wsize),
                "read_message_size": int(rsize),
                "num_threads": int(nthr),
                "duration": len(results),
            },
        )

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
            results, data = self._parse_stdout(stdout)
            documents = self._json_payload(results, data, s)
            if len(documents) > 0:
                for document in documents:
                    yield document, "results"
            logger.info(data)
            logger.info(stdout)
            logger.info("Finished executing sample %d out of %d" % (s, self.sample))
