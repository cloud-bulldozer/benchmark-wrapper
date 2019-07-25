#!/usr/bin/env python

import argparse
import sys
import subprocess
import os
import re
import elasticsearch


def _run_hammerdb():
    cmd = "cd /home/mkarg/Downloads/hammer/HammerDB-3.2/ && ./hammerdbcli auto setupdb.tcl"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return stdout.strip(), process.returncode

def _fake_run():
    with open("hammerdb.log", "r") as input:
        stdout = input.read()
    return stdout,0

def _parse_stdout(stdout):
    data = []
    iteration = 0
    for line in stdout.splitlines():
        if "TEST RESULT" in line:
            worker = (line.split(":"))[0]
            tpm = (line.split(" "))[6]
            nopm = (line.split(" "))[-2]
            entry = [ worker, tpm, nopm]
            data.append(entry)
    return data

def _json_payload(data, iteration, uuid, remote_ip, runtime, rampup, workers, warehouses, protocol, test_type):
    processed = []
    for i in range(0,len(data)):
        processed.append({
            "workload" : "hammerdb",
            "uuid" : uuid,
            "iteration": int(iteration),
            "remote_ip" : remote_ip,
            "runtime": runtime,
            "rampup": rampup,
            "num_workers": (len(data) -1),
            "worker": data[i][0],
            "tpm": data[i][1],
            "nopm": data[i][2],
            "warehouses": warehouses,
            "protocol": protocol,
            "test_type": test_type
            })
    return processed

def _summarize_data(data):
    for i in range(0,len(data)):
        entry = data[0]

        print("+{} HammerDB Results {}+".format("-"*(50), "-"*(50)))
        print("Run : {}".format(entry['iteration']))
        print("HammerDB setup")
        print("""
              server: {}""".format(entry['remote_ip']))
        print("")
        print("HammerDB results for:")
        print("""
              test_type: {}
              protocol: {}
              workers: {}
              worker: {}""".format(entry['test_type'],
                                     entry['protocol'],
                                     entry['num_workers'],
                                     entry['worker']))
        print("HammerDB results (TPM):")
        print("""
              TPM: {}""".format(entry['tpm']))
        print("HammerDB results (NOPM):")
        print("""
              NOPM: {}""".format(entry['nopm']))
        print("+{}+".format("-"*(115)))

def _index_result(server, port, payload):
    index = "hammerdb-results"
    es = elasticsearch.Elasticsearch([
        {'host': server, 'port': port}], send_get_body_as='POST')
    for result in payload:
        es.index(index=index, doc_type="result", body=result)

def main():
    parser = argparse.ArgumentParser(description="HammerDB Wrapper script")
    parser.add_argument(
            '-d', '--duration', nargs=1,
            help='Duration of a test run')
    parser.add_argument(
            '-r', '--rampup', nargs=1,
            help='Rampup time for the run')
    args = parser.parse_args()

    server = "bullwinkle-elk.rdu.openstack.engineering.redhat.com"
    port = "9200"
    protocol = "tcp"
    uuid = ""
    user = ""
    db = ""
    workers = ""
    warehouses = ""
    runtime = ""
    rampup = ""
    iteration = "1" # needs to be changed, comes from the caller
    test_type = "tpc-c"
    remote_ip = ""

    #stdout = _run_hammerdb() 
    stdout = _fake_run()
    if stdout[1] == 1:
        print "hammerdbcli failed to execute, trying one more time.."
        stdout = _fake_run()
        if stdout[1] == 1:
            print "hammerdbcli failed to execute a second time, stopping..."
            exit(1)
    data = _parse_stdout(stdout[0])
    documents = _json_payload(data, iteration, uuid, remote_ip, runtime, rampup, workers, warehouses, protocol, test_type)
    if server != "" :
        if len(documents) > 0 :
            print "Indexing data"
            _index_result(server,port,documents)
    if len(documents) > 0 :
        _summarize_data(documents)


if __name__ == '__main__':
    sys.exit(main())