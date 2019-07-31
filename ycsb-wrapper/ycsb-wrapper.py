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
import numpy as np
import re
import os
import subprocess
import sys

def _index_result(server,port,index,payload):
    try :
        es = elasticsearch.Elasticsearch([
            {'host': server,'port': port }],send_get_body_as='POST')
        for result in payload :
            print result
            es.index(index=index,doc_type="result", body=result)
    except Exception as e:
        print "An unknown error occured connecting to ElasticSearch: {}".format(e)
        return False

def _run(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return [ stdout.strip(), stderr.strip(), process.returncode]

def _json_payload(data,iteration,uuid,user,phase,workload,driver,recordcount,operationcount):
    processed = []
    summary = []
    for result in data['results'] :
        for action in result[3].split("["):
            bits = action.split(" ")
            if len(bits) < 2 :
                continue
            if bits[0][len(bits[0])-1] != ':':
                continue
            _date = result[0].split(" ")[0].split("-")
            _time = result[0].split(" ")[1].split(":")
            if len(bits) >= 8 :
                processed.append({
                    "workload" : "ycsb",
                    "uuid": uuid,
                    "user": user,
                    "phase": phase,
                    "driver": driver,
                    "timestamp": datetime(int(_date[0]),
                                          int(_date[1]),
                                          int(_date[2]),
                                          int(_time[0]),
                                          int(_time[1]),
                                          int(_time[2]),
                                          int(_time[3])),
                    "overall_rate": float(result[2].split(" ")[0]),
                    "action": bits[0][:-1],
                    "count": int(bits[1].split("=")[1][:-1]),
                    "latency_90": int(bits[5].split("=")[1][:-1]),
                    "latency_min": int(bits[3].split("=")[1][:-1]),
                    "latency_max": int(bits[2].split("=")[1][:-1]),
                    "recordcount": int(recordcount),
                    "operationcount": int(operationcount),
                    "iteration" : int(iteration),
                    "workload_type": workload
        })
    summary_dict = {}
    if 'summary' in data :
        for summ in data['summary'] :
            if summ[0][0].isdigit() or summ[0][0] is "I" :
                continue
            if not summ[0].strip('[').strip(']') in summary_dict :
                summary_dict[summ[0].strip('[').strip(']')] = {}
            summary_dict[summ[0].strip('[').strip(']')][summ[1]] = float(summ[2])
        summary.append({
            "workload" : "ycsb",
            "uuid": uuid,
            "user": user,
            "phase": phase,
            "driver": driver,
            "timestamp": datetime.now(),
            "data": summary_dict,
            "recordcount": int(recordcount),
            "operationcount": int(operationcount),
            "iteration" : int(iteration),
            "workload_type": workload
        })
    return processed, summary


def _parse_stdout(data):
    data_points = re.findall(r"(\d+-\d+-\d+ \d+:\d+:\d+:\d+) \d+ sec: (\d+ operations); (\d+.\d+? current ops/sec); (.*)",data)
    summary = re.findall(r"(.*), (.*), (.*)",data)
    return { "results": data_points, "summary": summary }


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
    recordcount = ""
    operationcount = ""
    phase = ""

    if "es" in os.environ :
        server = os.environ["es"]
        port = os.environ["es_port"]
        uuid = os.environ["uuid"]
    if "user" in os.environ :
        user = os.environ["user"]
    if "workload" in os.environ :
        workload = os.environ["workload"]
    if "num_records" in os.environ :
        recordcount = os.environ["num_records"]
    if "num_operations" in os.environ :
        operationcount = os.environ["num_operations"]

    extra = ""
    if not args.extra is None:
        extra = args.extra[0]

    if args.load :
        phase = "load"
        cmd = "/ycsb/bin/ycsb {} {} -s -P /tmp/ycsb/{} {}".format(phase,
                                                                        args.driver[0],
                                                                        args.workload[0],
                                                                        extra)
        stdout = _run(cmd)
        output = "{}\n{}".format(stdout[0],stdout[1])
    else:
        phase = "run"
        cmd = "/ycsb/bin/ycsb {} {} -s -P /tmp/ycsb/{} {}".format(phase,
                                                                        args.driver[0],
                                                                        args.workload[0],
                                                                        extra)
        stdout = _run(cmd)
        output = "{}\n{}".format(stdout[0],stdout[1])

    if stdout[2] != 0 :
        print "YCSB failed to execute"
        exit(1)
    if "Error inserting" in stdout[1] :
        print "YCSB failed to load database... Drop previous YCSB database"
        exit(1)

    data = _parse_stdout(output)
    print output
    documents,summary = _json_payload(data,args.run[0],uuid,user,phase,workload,args.driver[0],recordcount,operationcount)
    if server != "" :
        print "Attempting to index results..."
        if len(documents) > 0 :
            index = "ripsaw-ycsb-results"
            _index_result(server,port,index,documents)
        if len(summary) > 0 :
            index = "ripsaw-ycsb-summary"
            _index_result(server,port,index,summary)

if __name__ == '__main__':
    sys.exit(main())
