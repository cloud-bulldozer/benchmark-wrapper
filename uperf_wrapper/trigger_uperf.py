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

import re
import subprocess
from datetime import datetime

import numpy as np


class Trigger_uperf():
    def __init__(self, args):
        self.uuid = args.uuid[0]
        self.user = args.user[0]
        self.clientips = args.clientips
        self.remoteip = args.remoteip
        self.hostnetwork = args.hostnetwork
        self.serviceip = args.serviceip
        self.server_node = args.server_node
        self.client_node = args.client_node
        self.cluster_name = args.cluster_name
        self.workload = args.workload
        self.run = args.run
        self.resourcetype = args.resourcetype

    def _json_payload(self, data, iteration, uuid, user, hostnetwork, serviceip, remote, client,
                      clustername, resource_type, server_node, client_node):
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
                "uuid": uuid,
                "user": user,
                "cluster_name": clustername,
                "hostnetwork": hostnetwork,
                "iteration": int(iteration),
                "remote_ip": remote,
                "client_ips": client,
                "uperf_ts": datetime.fromtimestamp(int(result[0].split('.')[0]) / 1000),
                "test_type": data['test'],
                "protocol": data['protocol'],
                "service_ip": serviceip,
                "message_size": int(data['message_size']),
                "num_threads": int(data['num_threads']),
                "duration": len(data['results']),
                "bytes": int(result[1]),
                "norm_byte": int(result[1]) - prev_bytes,
                "ops": int(result[2]),
                "norm_ops": norm_ops,
                "norm_ltcy": norm_ltcy,
                "kind": str(resource_type),
                "client_node": client_node,
                "server_node": server_node
            })
            prev_timestamp = float(result[0])
            prev_bytes = int(result[1])
            prev_ops = int(result[2])
        return processed

    def _run_uperf(self, workload):
        cmd = "uperf -v -a -x -i 1 -m {}".format(workload)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), process.returncode

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

    def _summarize_data(self, data):
        byte = []
        op = []
        ltcy = []

        for entry in data:
            byte.append(entry["norm_byte"])
            op.append(entry["norm_ops"])
            ltcy.append(entry["norm_ltcy"])

        byte_result = np.array(byte)
        op_result = np.array(op)
        ltcy_result = np.array(ltcy)

        data = data[0]
        print("+{} UPerf Results {}+".format("-" * (50), "-" * (50)))
        print("Run : {}".format(data['iteration']))
        print("Uperf Setup")
        print("""
              hostnetwork : {}
              client: {}
              server: {}""".format(data['hostnetwork'],
                                   data['client_ips'],
                                   data['remote_ip']))
        print("")
        print("UPerf results for :")
        print("""
              test_type: {}
              protocol: {}
              message_size: {}
              num_threads: {}""".format(data['test_type'],
                                        data['protocol'],
                                        data['message_size'],
                                        data['num_threads']))
        print("")
        print("UPerf results (bytes/sec):")
        print("""
              min: {}
              max: {}
              median: {}
              average: {}
              95th: {}""".format(np.amin(byte_result),
                                 np.amax(byte_result),
                                 np.median(byte_result),
                                 np.average(byte_result),
                                 np.percentile(byte_result, 95)))
        print("")
        print("UPerf results (ops/sec):")
        print("""
              min: {}
              max: {}
              median: {}
              average: {}
              95th: {}""".format(np.amin(op_result),
                                 np.amax(op_result),
                                 np.median(op_result),
                                 np.average(op_result),
                                 np.percentile(op_result, 95)))

        print("")
        print("UPerf Latency results (microseconds):")
        print("""
              min: {}
              max: {}
              median: {}
              average: {}
              95th: {}""".format(np.amin(ltcy_result),
                                 np.amax(ltcy_result),
                                 np.median(ltcy_result),
                                 np.average(ltcy_result),
                                 np.percentile(ltcy_result, 95)))
        print("+{}+".format("-" * (115)))

    def emit_actions(self):
        stdout = self._run_uperf(self.workload[0])
        if stdout[1] == 1:
            print("UPerf failed to execute, trying one more time..")
            stdout = self._run_uperf(self.workload[0])
            if stdout[1] == 1:
                print("UPerf failed to execute a second time, stopping...")
                exit(1)
        data = self._parse_stdout(stdout[0])
        documents = self._json_payload(data, self.run[0], self.uuid, self.user, self.hostnetwork,
                                       self.serviceip,
                                       self.remoteip,
                                       self.clientips, self.cluster_name, self.resourcetype[0],
                                       self.server_node,
                                       self.client_node)
        if len(documents) > 0:
            for document in documents:
                yield document, 'results'
        print(stdout[0])
        if len(documents) > 0:
            self._summarize_data(documents)
