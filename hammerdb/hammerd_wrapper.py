#!/usr/bin/env python

import argparse
import sys
import subprocess
import os
import re
import elasticsearch


def _run_hammerdb():
    cmd = "cd /hammer; ./hammerdbcli auto /workload/tpcc-workload.tcl"
    #cmd = "cd ~/Downloads/hammer/HammerDB-3.2; ./hammerdbcli auto workload.tcl"
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
        print (line)
        if "TEST RESULT" in line:
            worker = (line.split(":"))[0]
            print (worker)
            tpm = (line.split(" "))[6]
            nopm = (line.split(" "))[-2]
            entry = [ worker, tpm, nopm]
            data.append(entry)
    return data

def _json_payload(data, iteration, uuid, db_server, db_port, db_warehouses, db_num_workers, transactions, test_type, runtime, rampup, samples):
    processed = []
    for i in range(0,len(data)):
        processed.append({
            "workload" : "hammerdb",
            "uuid" : uuid,
            "iteration": int(iteration),
            "db_server" : db_server,
            "db_port" : db_port,
            "db_warehouses" : db_warehouses,
            "db_num_workers" : db_num_workers,
            "transactions": transactions,
            "test_type": test_type,
            "runtime": runtime,
            "rampup": rampup,
            "samples": samples,
            "num_workers": (len(data) -1),
            "worker": data[i][0],
            "tpm": data[i][1],
            "nopm": data[i][2]
            })
    return processed

def _summarize_data(data):
    for i in range(0,len(data)):
        entry = data[0]

        print("+{} HammerDB Results {}+".format("-"*(50), "-"*(50)))
        print("Run : {}".format(entry['iteration']))
        print("HammerDB setup")
        #print("""
        #      server: {}""".format(entry['remote_ip']))
        print("")
        print("HammerDB results for:")
        print("Database server: {}".format(entry['db_server']))
        print("Database port: {}".format(entry['db_port']))
        print("Database warehouses: {}".format(entry['db_warehouses']))
        print("Database workers: {}".format(entry['db_num_workers']))
        print("Transactions: {}".format(entry['transactions']))
        print("Worker: {}".format(entry['worker']))
        print("Samples: {}".format(entry['samples']))
        print("Test type: {}".format(entry['test_type']))
        #print("""
        #      test_type: {}
        #      protocol: {}
        #      workers: {}
        #      worker: {}""".format(entry['test_type'],
        #                             entry['num_workers'],
        #                             entry['worker']))
        print("HammerDB results (TPM):")
        print("""
              TPM: {}""".format(entry['tpm']))
        print("HammerDB results (NOPM):")
        print("""
              NOPM: {}""".format(entry['nopm']))
        print("+{}+".format("-"*(115)))

def _index_result(index,server,port,payload):
    _es_connection_string = str(server) + ':' + str(port)
    es = elasticsearch.Elasticsearch([_es_connection_string],send_get_body_as='POST')
    for result in payload:
        es.index(index=index, body=result)

def main():
    parser = argparse.ArgumentParser(description="HammerDB Wrapper script")
    parser.add_argument(
            '-d', '--duration', nargs=1,
            help='Duration of a test run')
    parser.add_argument(
            '-r', '--rampup', nargs=1,
            help='Rampup time for the run')
    args = parser.parse_args()

    #server = "bullwinkle-elk.rdu.openstack.engineering.redhat.com"
    server = "marquez.perf.lab.eng.rdu2.redhat.com"
    port = "9200"
    protocol = "tcp"
    uuid = ""
    db_user = ""
    db_server = ""
    db_port = ""
    db_warehouses = ""
    db_num_workers = ""
    transactions = ""
    runtime = ""
    rampup = ""
    samples = ""
    iteration = "1" # needs to be changed, comes from the caller
    test_type = "tpc-c"

    if "uuid" in os.environ:
        uuid = os.environ["uuid"]
    if "db_user" in os.environ:
        db_user = os.environ["db_user"]
    if "db_server" in os.environ:
        db_server = os.environ["db_server"]
    if "db_port" in os.environ:
        db_port = os.environ["db_port"]
    if "db_warehouses" in os.environ:
        db_warehouses = os.environ["db_warehouses"]
    if "db_num_workers" in os.environ:
        db_num_workers = os.environ["db_num_workers"]
    if "transactions" in os.environ:
        transactions = os.environ["transactions"]
    if "runtime" in os.environ:
        runtime = os.environ["runtime"]
    if "rampup" in os.environ:
        rampup = os.environ["rampup"]
    if "samples" in os.environ:
        samples = os.environ["samples"]


    stdout = _run_hammerdb()
    #stdout = _fake_run()
    if stdout[1] == 1:
        print ("hammerdbcli failed to execute, trying one more time..")
        stdout = _fake_run()
        if stdout[1] == 1:
            print ("hammerdbcli failed to execute a second time, stopping...")
            exit(1)
    data = _parse_stdout(stdout[0])
    documents = _json_payload(data, iteration, uuid, db_server, db_port, db_warehouses, db_num_workers, transactions, test_type, runtime, rampup, samples)
    if server != "" :
        if len(documents) > 0 :
            _index_result("ripsaw-hammerdb-results",server,port,documents)
    if len(documents) > 0 :
        _summarize_data(documents)


if __name__ == '__main__':
    sys.exit(main())
