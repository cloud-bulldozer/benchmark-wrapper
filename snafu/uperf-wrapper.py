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
from datetime import datetime
import numpy as np
from common.elastic import  *
from common.common import *
import re
import sys

def _json_payload(data,iteration,uuid,user,hostnetwork,serviceip,remote,client):
    processed = []
    prev_bytes = 0
    prev_ops = 0
    for result in data['results'] :
        processed.append({
            "workload" : "uperf",
            "uuid": uuid,
            "user": user,
            "hostnetwork": hostnetwork,
            "iteration" : int(iteration),
            "remote_ip": remote,
            "client_ips" : client,
            "uperf_ts" : datetime.fromtimestamp(int(result[0].split('.')[0])/1000),
            "test_type": data['test'],
            "protocol": data['protocol'],
            "service_ip": serviceip,
            "message_size": int(data['message_size']),
            "duration": len(data['results']),
            "bytes": int(result[1]),
            "norm_byte": int(result[1])-prev_bytes,
            "ops": int(result[2]),
            "norm_ops": int(result[2])-prev_ops
        })
        prev_bytes = int(result[1])
        prev_ops = int(result[2])
    return processed

def _parse_stdout(stdout):
    # This will effectivly give us:
    # ripsaw-test-stream-udp-16384
    config = re.findall(r"running profile:(.*) \.\.\.",stdout)
    test = re.split("-",config[0])[0]
    protocol = re.split("-",config[0])[1]
    size = re.split("-",config[0])[2]
    # This will yeild us this structure :
    #     timestamp, number of bytes, number of operations
    # [('1559581000962.0330', '0', '0'), ('1559581001962.8459', '4697358336', '286704') ]
    results = re.findall(r"timestamp_ms:(.*) name:Txn2 nr_bytes:(.*) nr_ops:(.*)",stdout)
    return { "test": test, "protocol": protocol, "message_size": size, "results" : results }

def _summarize_data(data):

    byte = []
    op = []

    for entry in data :
        byte.append(entry["norm_byte"])
        op.append(entry["norm_ops"])

    byte_result = np.array(byte)
    op_result = np.array(op)

    data = data[0]
    print("+{} UPerf Results {}+".format("-"*(50), "-"*(50)))
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
          message_size: {}""".format(data['test_type'],
                                     data['protocol'],
                                     data['message_size']))
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
    print("+{}+".format("-"*(115)))

def main():
    workload = "uperf"
    parser = argparse.ArgumentParser(description="UPerf Wrapper script")
    parser.add_argument(
        '-w', '--workload', nargs=1,
        help='Provide XML workload location')
    parser.add_argument(
        '-r', '--run', nargs=1,
        help='Provide the iteration for the run')
    args = parser.parse_args()

    server = ""
    uuid = ""
    user = ""
    clientips = ""
    remoteip = ""
    hostnetwork = ""
    serviceip = ""
    es = {}

    if "serviceip" in os.environ:
        serviceip = os.environ['serviceip']
    if "es" in os.environ :
        es['server'] = os.environ["es"]
        es['port'] = os.environ["es_port"]
        uuid = os.environ["uuid"]
    if "test_user" in os.environ :
        user = os.environ["test_user"]
    if "hostnet" in os.environ:
        hostnetwork = os.environ["hostnet"]
    if "h" in os.environ:
        remoteip = os.environ["h"]
    if "ips" in os.environ:
        clientips = os.environ["ips"]

    cmd = "uperf -v -a -x -i 1 -m {}".format(args.workload[0])
    stdout = run(cmd)
    if stdout[1] != 0 :
        print "UPerf failed to execute, trying one more time.."
        stdout = run(cmd)
        if stdout[1] != 0:
            print "UPerf failed to execute a second time, stopping..."
            exit(1)
    data = _parse_stdout(stdout[0])
    documents = _json_payload(data,args.run[0],uuid,user,hostnetwork,serviceip,remoteip,clientips)
    if server != "" :
        if len(documents) > 0 :
            index = "uperf-results"
            index_result(es,workload,documents)
    print stdout[0]
    if len(documents) > 0 :
      _summarize_data(documents)

if __name__ == '__main__':
    sys.exit(main())
