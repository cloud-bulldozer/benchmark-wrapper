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
from common.elastic import  *
from common.common import *
import re
import os
import sys
import pprint

def _json_payload(data,iteration,uuid,user,phase,workload,recordcount,operationcount):
    processed = []
    for result in data['results'] :
        processed.append({
            "workload" : "ycsb",
            "uuid": uuid,
            "user": user,
            "phase": phase,
            "recordcount": recordcount,
            "operationcount": operationcount,
            "iteration" : int(iteration),
            "workload_type": workload
        })
    return processed

def _parse_stdout(stdout):
    data_points = re.findall(r"(\d+-\d+-\d+ \d+:\d+:\d+:\d+) \d+ sec: (\d+ operations); (\d+.\d? current ops/sec); ([[A-Z]+:.*])+ ",data)
    summary = re.findall(r"[([[A-Z]+]), (.*), (.*)",data)
    return { "results": data_points, "summary": summary }

def _summarize_data(data):

    print("+{} YCSB Results {}+".format("-"*(50), "-"*(50)))
    print("Run : {}".format(data['iteration']))
    print("YCSB Setup")
    print("""
          workload: {}
          num_records: {}
          num_operations: {}""".format(data['workload'],
                               data['num_records'],
                               data['num_operations']))
    print("")
    print("YCSB results (ops/sec):")
    print("""
          min: {}
          max: {}
          median: {}
          average: {}
          """.format(np.amin(op_result),
                             np.amax(op_result),
                             np.median(op_result),
                             np.average(op_result),
                             ))
    print("+{}+".format("-"*(115)))

def main():
    parser = argparse.ArgumentParser(description="YCSB Wrapper script")
    parser.add_argument(
        '-r', '--run', nargs=1,
        help='Provide the iteration for the run')
    parser.add_argument(
        '-l', '--load', action='store_true',default=False,
        help='Run the load phase?')
    parser.add_argument(
        '-d', '--driver', nargs=1,
        help='Which YCSB Driver, eg mongodb')
    parser.add_argument(
        '-w', '--workload', nargs=1,
        help='Which YCSB workload, eg workloada')
    parser.add_argument(
        '-x', '--extra', nargs=1,
        help='Extra params to pass')

    args = parser.parse_args()
    if args.driver is None :
        parser.print_help()
        exit(1)

    server = ""
    uuid = ""
    user = ""
    workload = ""
    num_operations = ""
    num_records = ""
    phase = ""

    if "es" in os.environ :
        server = os.environ["es"]
        port = os.environ["es_port"]
        uuid = os.environ["uuid"]
    if "test_user" in os.environ :
        user = os.environ["test_user"]
    if "workload" in os.environ :
        workload = os.environ["workload"]
    if "num_records" in os.environ :
        num_records = os.environ["num_records"]
    if "num_operations" in os.environ :
        num_operations= os.environ["num_records"]

    extra = ""
    if not args.extra is None:
        extra = args.extra[0]

    if args.load :
        phase = "load"
        cmd = "/ycsb/bin/ycsb {} {} -s -P /ycsb/workloads/{} {}".format(phase,
                                                                        args.driver[0],
                                                                        args.workload[0],
                                                                        extra)
        stdout = run(cmd)
    else:
        phase = "run"
        cmd = "/ycsb/bin/ycsb {} {} -s -P /ycsb/workloads/{} {}".format(phase,
                                                                        args.driver[0],
                                                                        args.workload[0],
                                                                        extra)
        stdout = run(cmd)

    if stdout[1] != 0 :
        print "YCSB failed to execute"
        exit(1)
    data = _parse_stdout(stdout[0])
    pprint.pprint(data)
    documents = _json_payload(data,args.run[0],uuid,user,phase,workload,recordcount,operationcount)
    if server != "" :
        if len(documents) > 0 :
            _index_result(server,port,documents)
    print stdout[0]
    if len(documents) > 0 :
      _summarize_data(documents)

if __name__ == '__main__':
    sys.exit(main())
