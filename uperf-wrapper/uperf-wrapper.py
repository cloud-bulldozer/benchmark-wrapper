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
import elasticsearch
import re
import os
import subprocess
import sys

def _index_result(server,port,payload):
    index = "uperf-results"
    es = elasticsearch.Elasticsearch([
        {'host': server,'port': port }],send_get_body_as='POST')
    for result in payload:
         es.index(index=index, doc_type="result", body=result)

def _json_payload(data,iteration,uuid,user,hostnetwork,remote,client):
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

def _run_uperf(workload):
    cmd = "uperf -v -a -x -i 1 -m {}".format(workload)
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return stdout.strip()

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

def main():
    parser = argparse.ArgumentParser(description="UPerf Wrapper script")
    parser.add_argument(
        '-w', '--workload', nargs=1,
        help='Provide XML workload location')
    parser.add_argument(
        '-r', '--run', nargs=1,
        help='Provide the iteration for the run')
    parser.add_argument(
        '-e', '--elasticsearch', nargs='?',
        help='Elasticsearch host')
    parser.add_argument(
        '-p', '--elasticport', nargs='?',
        help='Elasticsearch port')
    parser.add_argument(
        '-i', '--elasticindex', nargs='?',
        help='Elasticsearch index')
    args = parser.parse_args()

    server = os.environ["es"]
    port = os.environ["es_port"]
    user = os.environ["user"]
    uuid = os.environ["uuid"]
    hostnetwork = os.environ["hostnet"]
    remoteip = os.environ["h"]
    clientips = os.environ["ips"]
    stdout = _run_uperf(args.workload[0])
    data = _parse_stdout(stdout)
    documents = _json_payload(data,args.run[0],uuid,user,hostnetwork,remoteip,clientips)
    if ( server != "" ):
      _index_result(server,port,documents)
    print stdout

if __name__ == '__main__':
    sys.exit(main())
