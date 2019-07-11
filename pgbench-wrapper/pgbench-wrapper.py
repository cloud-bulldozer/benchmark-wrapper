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
import base64

def _index_result(server,port,payload):
    index = "pgbench-results"
    es = elasticsearch.Elasticsearch([
        {'host': server,'port': port }],send_get_body_as='POST')
    for result in payload:
         es.index(index=index, doc_type="result", body=result)

def _json_payload(data,iteration,uuid,user,numclients,database):
    processed = []
    processed.append({
        "workload": "pgbench",
        "uuid": uuid,
        "user": user,
        "iteration": int(iteration),
        "database": database,
        "numclients": numclients,
        "tps_incl_con_est": data[tps][0][0],
        "tps_excl_con_est": data[tps][1][0]
    })
    for line in data[config]:
        processed.append({
            "{}".format(line[0]): line[1]
        })
    return processed

def _run_pgbench():
    cmd = "pgbench $pgbench_opts"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return stdout.strip(), process.returncode

def _parse_stdout(stdout):
    raw_output_b64 = base64.b64encode(stdout)
    # All pgbench config values are output on separate lines
    # in a 'key: value' format. Matching on the colon.
    # This should provide us a structure like:
    # [['transaction_type', 'TPC-B (sort of)'],['scaling_factor', '50'],...]
    config = re.findall(r": ",stdout)
    for idx, line in enumerate(config):
        config[idx] = line.split(':')
        config[idx][0] = config[idx][0].replace(" ", "_")
    # This will yeild us this structure:
    #     tps, condition
    # [('2394.718707', 'including connections establishing'), ('2394.874350', 'excluding connections establishing')]
    tps = re.findall(r"tps = (.*) \((.*)\)")
    return { "config": config, "tps": tps, "raw_output_b64": raw_output_b64 }

def _summarize_data(data,iteration,numclients,database):
    print("+{} PGBench Results {}+".format("-"*(50), "-"*(50)))
    print("Run: {}".format(iteration))
    print("PGBench Config:")
    for line in data['config']:
        print(line)
    print("")
    print("PGBench results for:")
    print("""
          database: {}
          numclients: {}""".format(database, numclients))
    print("")
    print("PGBench results (tps):")
    print("""
          {}: {}
          {}: {}""".format(data['tps'][0][1], data['tps'][0][0],
                           data['tps'][1][1], data['tps'][1][0]))
    print("+{}+".format("-"*(115)))

def main():
    parser = argparse.ArgumentParser(description="PGBench Wrapper script")
    parser.add_argument(
        '-r', '--run', nargs=1,
        help='Provide the iteration for the run')
    args = parser.parse_args()

    server = ""
    port = ""
    uuid = ""
    user = ""
    numclients = ""
    database = ""

    if "es" in os.environ :
        server = os.environ["es"]
        port = os.environ["es_port"]
        uuid = os.environ["uuid"]
    if "test_user" in os.environ :
        user = os.environ["test_user"]
    if "numclients" in os.environ:
        numclients = os.environ["numclients"]
    if "database" in os.environ:
        database = os.environ["database"]

    stdout = _run_pgbench()
    if stdout[1] == 1 :
        print "PGBench failed to execute, trying one more time.."
        stdout = _run_pgbench()
        if stdout[1] == 1:
            print "PGBench failed to execute a second time, stopping..."
            exit(1)
    data = _parse_stdout(stdout[0])
    documents = _json_payload(data,args.run[0],uuid,user,numclients,database)
    if server != "" :
        if len(documents) > 0 :
            _index_result(server,port,documents)
    print stdout[0]
    if len(documents) > 0 :
      _summarize_data(data,args.run[0],numclients,database)

if __name__ == '__main__':
    sys.exit(main())
