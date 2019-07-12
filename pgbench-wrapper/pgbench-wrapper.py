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

def _json_payload(data,iteration,uuid,user,database,pgb_vers):
    processed = []
    processed.append({
        "workload": "pgbench",
        "pgb_vers": pgb_vers,
        "uuid": uuid,
        "user": user,
        "iteration": int(iteration),
        "database": database,
        "raw_output_b64": data['raw_output_b64'],
    })
    for line in data['config']:
        processed[0].update({
            "{}".format(line[0]): line[1]
        })
    for line in data['results']:
        processed[0].update({
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
    # pgbench outputs config values and results in either 'key:value'
    # or 'key=value' format. It's a bit inconsistent between versions
    # which information uses which format, and some of the output is
    # config info and some is benchmark results.
    #
    # We normalize everything to 'key:value' first, then extract from
    # the new list the outputs that are results and place them in a
    # new list.
    results = []
    config = stdout.splitlines()
    for idx, line in enumerate(config):
        config[idx] = line.replace(' = ',':').split(':',1)
        config[idx][0] = config[idx][0].replace(" ", "_")
        if re.search('tps|latency|processed',config[idx][0]):
            results.append(config[idx])
    for idx, line in enumerate(results):
        if line in config:
            config.remove(line)
        if re.search('tps',results[idx][0]):
            cons=re.findall('.*\((....)uding.*',results[idx][1])
            if cons:
                results[idx][0] = 'tps_{}_con_est'.format(cons[0])
                results[idx][1] = re.sub(' \(.*', '', results[idx][1])
    return { "config": config, "results": results, "raw_output_b64": raw_output_b64 }

def _summarize_data(data,iteration,uuid,database,pgb_vers):
    print("+{} PGBench Results {}+".format("-"*(50), "-"*(50)))
    print("PGBench version: {}".format(pgb_vers))
    print("")
    print("UUID: {}".format(uuid))
    print("Run: {}".format(iteration))
    print("")
    print("Database: {}".format(database))
    print("")
    print("PGBench run info:")
    for line in data['config']:
        print("          {}: {}".format(line[0], line[1]))
    print("")
    # I asked for a mai tai, and they brought me a pina colada,
    # and I said no salt, NO salt on the margarita, but it had salt
    # on it, big grains of salt, floating in the glass.
    print("TPS report:") 
    for line in data['results']:
        print("          {}: {}".format(line[0], line[1]))
    print("")
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
    database = ""
    pgb_vers = ""

    if "es" in os.environ:
        server = os.environ["es"]
        port = os.environ["es_port"]
    if "uuid" in os.environ:
        uuid = os.environ["uuid"]
    if "test_user" in os.environ:
        user = os.environ["test_user"]
    if "database" in os.environ:
        database = os.environ["database"]
    if "pgb_vers" in os.environ:
        pgb_vers = os.environ["pgb_vers"]

    stdout = _run_pgbench()
    if stdout[1] == 1 :
        print "PGBench failed to execute, trying one more time.."
        stdout = _run_pgbench()
        if stdout[1] == 1:
            print "PGBench failed to execute a second time, stopping..."
            exit(1)
    data = _parse_stdout(stdout[0])
    documents = _json_payload(data,args.run[0],uuid,user,database,pgb_vers)
    if server != "" :
        if len(documents) > 0 :
            _index_result(server,port,documents)
    print stdout[0]
    if len(documents) > 0 :
      _summarize_data(data,args.run[0],uuid,database,pgb_vers)
    print(documents)

if __name__ == '__main__':
    sys.exit(main())
