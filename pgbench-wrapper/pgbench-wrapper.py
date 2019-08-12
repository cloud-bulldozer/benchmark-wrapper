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
import copy
import base64

def _index_result(index,server,port,payload):
    index = index
    es = elasticsearch.Elasticsearch([
        {'host': server,'port': port }],send_get_body_as='POST')
    indexed=True
    processed_count = 0
    total_count = 0
    for result in payload:
        try:
            es.index(index=index, doc_type="_doc", body=result)
            processed_count += 1
        except Exception as e:
            print(repr(e) + "occurred for the json document:")
            print(str(result))
            indexed=False
        total_count += 1
    return indexed, processed_count, total_count

def _json_payload(meta_processed,data):
    processed = copy.deepcopy(meta_processed)
    for line in data['config']:
        processed[0].update({
            "{}".format(line[0]): _num_convert(line[1])
        })
    for line in data['results']:
        processed[0].update({
            "{}".format(line[0]): _num_convert(line[1])
        })
    return processed

def _json_payload_raw(meta_processed,data):
    processed = copy.deepcopy(meta_processed)
    for line in data['config']:
        processed[0].update({
            "{}".format(line[0]): _num_convert(line[1])
        })
    processed[0].update({
        "raw_output_b64": str(data['raw_output_b64'])
    })
    return processed

def _json_payload_prog(meta_processed,progress,data):
    processed = []
    for prog in progress:
        entry = copy.copy(meta_processed[0])
        for line in data['config']:
            if 'timestamp' not in line[0]:
                entry.update({
                    "{}".format(line[0]): _num_convert(line[1])
                })
        entry.update(prog)
        processed.append(entry)
    return processed

def _run_pgbench():
    cmd = "pgbench -P 10 --progress-timestamp $pgbench_opts"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return stdout.strip(), stderr.strip(), process.returncode

def _num_convert(value):
    try:
        value = int(value)
    except ValueError:
        try:
            value = float(value)
        except:
            pass
    except TypeError:
        pass
    return value


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
        config[idx][0] = config[idx][0].replace(" ", "_").strip()
        config[idx][1] = _num_convert(config[idx][1].strip())
        if re.search('tps|latency|processed',config[idx][0]):
            results.append(config[idx])
        if re.search('duration',config[idx][0]):
            config[idx][0] += "_seconds"
            config[idx][1] = _num_convert(config[idx][1].split()[0])
    for idx, line in enumerate(results):
        if line in config:
            config.remove(line)
        if re.search('tps',results[idx][0]):
            cons=re.findall('.*\((....)uding.*',results[idx][1])
            if cons:
                results[idx][0] = 'tps_{}_con_est'.format(cons[0]).strip()
                results[idx][1] = _num_convert(re.sub(' \(.*', '', results[idx][1]).strip())
        elif re.search('latency',results[idx][0]):
            results[idx][0] += "_ms"
            results[idx][1] = _num_convert(results[idx][1].split(" ",1)[0])
        elif re.search('processed',results[idx][0]):
            try:
                results[idx][1] = _num_convert(results[idx][1].split("/",1)[0])
            except AttributeError:
                pass
    config.append(["timestamp", datetime.now()])
    return { "config": config, "results": results, "raw_output_b64": raw_output_b64 }

def _parse_stderr(stderr):
    progress = []
    for line in stderr.splitlines():
        if "progress" in line:
            progress.append({
                "timestamp": datetime.fromtimestamp(float(line.split(" ")[1])),
                "tps": float(line.split(" ")[3]),
                "latency_ms": float(line.split(" ")[6]),
                "stddev": float(line.split(" ")[9])
            })
    return progress

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
    description = ""
    args.cluster_name = "mycluster"
    if "clustername" in os.environ:
        args.cluster_name = os.environ["clustername"]
    pgb_vers = subprocess.check_output("pgbench --version", shell=True).strip()
    run_start_timestamp = datetime.now()
    sample_start_timestamp = datetime.now()
    index = "ripsaw-pgbench"

    if "es" in os.environ:
        server = os.environ["es"]
        port = os.environ["es_port"]
        if "es_index_prefix" in os.environ:
            index = os.environ["es_index_prefix"]
    if "uuid" in os.environ:
        uuid = os.environ["uuid"]
    if "test_user" in os.environ:
        user = os.environ["test_user"]
    if "database" in os.environ:
        database = os.environ["database"]
    if "description" in os.environ:
        description = os.environ["description"]
    if "run_start_timestamp" in os.environ:
        run_start_timestamp = datetime.fromtimestamp(float(os.environ["run_start_timestamp"]))
    if "sample_start_timestamp" in os.environ:
        sample_start_timestamp = datetime.fromtimestamp(float(os.environ["sample_start_timestamp"]))

    # Initialize json payload shared metadata
    meta_processed = []
    meta_processed.append({
        "workload": "pgbench",
        "pgb_vers": pgb_vers,
        "uuid": uuid,
        "user": user,
        "cluster_name": args.cluster_name,
        "iteration": int(args.run[0]),
        "database": database,
        "run_start_timestamp": run_start_timestamp,
        "sample_start_timestamp": sample_start_timestamp,
        "description": description,
    })

    output = _run_pgbench()
    if output[2] == 1 :
        print "PGBench failed to execute, trying one more time.."
        output = _run_pgbench()
        if output[2] == 1:
            print "PGBench failed to execute a second time, stopping..."
            exit(1)
    data = _parse_stdout(output[0])
    progress = _parse_stderr(output[1])
    documents = _json_payload(meta_processed,data)
    documents_raw = _json_payload_raw(meta_processed,data)
    documents_prog = _json_payload_prog(meta_processed,progress,data)
    print output[0]
    if len(documents) > 0 :
      _summarize_data(data,args.run[0],uuid,database,pgb_vers)
    print("\n")
    print(documents)
    print("\n")
    if server != "" :
        if len(documents) > 0 :
            _status_results, processed_count, total_count = _index_result("{}-summary".format(index),server,port,documents)
            if _status_results:
                print("Succesfully indexed {} pgbench summary documents to index {}-summary\n".format(str(total_count),str(index)))
            else:
                print("{}/{} pgbench summary documents succesfully indexed to {}-summary\n".format(str(processed_count),str(total_count),str(index)))

            _status_results, processed_count, total_count = _index_result("{}-raw".format(index),server,port,documents_raw)
            if _status_results:
                print("Succesfully indexed {} pgbench raw documents to index {}-raw\n".format(str(total_count),str(index)))
            else:
                print("{}/{} pgbench raw documents succesfully indexed to {}-raw\n".format(str(processed_count),str(total_count),str(index)))

            _status_results, processed_count, total_count = _index_result("{}-results".format(index),server,port,documents_prog)
            if _status_results:
                print("Succesfully indexed {} pgbench results documents to index {}-results\n".format(str(total_count),str(index)))
            else:
                print("{}/{} pgbench results documents succesfully indexed to {}-results\n".format(str(processed_count),str(total_count),str(index)))
        else:
            print("Indexing failed; summary JSON document empty!\n")
    else:
        print("Results not indexed.\n")

if __name__ == '__main__':
    sys.exit(main())
