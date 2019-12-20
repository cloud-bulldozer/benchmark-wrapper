#!/usr/bin/env python

import argparse
import sys
import subprocess
import os
import re
import elasticsearch
import time 
from datetime import datetime

def _run_hammerdb():
    cmd = "cd /hammer; ./hammerdbcli auto /workload/tpcc-workload.tcl"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    stdout,stderr = process.communicate()
    return stdout.strip().decode("utf-8"), process.returncode

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
            entry = [ worker, tpm, nopm ]
            data.append(entry)
    return data

def _json_payload(data, uuid, db_server, db_port, db_warehouses, db_num_workers, db_tcp, db_user, transactions, test_type, runtime, rampup, samples, timed_test, timestamp):
    processed = []
    for i in range(0,len(data)):
        processed.append({
            "workload" : "hammerdb",
            "uuid" : uuid,
            "db_server" : db_server,
            "db_port" : db_port,
            "db_warehouses" : db_warehouses,
            "db_num_workers" : db_num_workers,
            "db_tcp": db_tcp,
            "db_user": db_user,
            "transactions": transactions,
            "test_type": test_type,
            "runtime": runtime,
            "rampup": rampup,
            "samples": samples,
            "timed_test": timed_test,
            "worker": data[i][0],
            "tpm": data[i][1],
            "nopm": data[i][2],
            "timestamp": timestamp
            })
    return processed

def _summarize_data(data):
    for i in range(0,len(data)):
        entry = data[0]

        print("+{} HammerDB Results {}+".format("-"*(50), "-"*(50)))
        print("HammerDB setup")
        print("")
        print("HammerDB results for:")
        print("UUID: {}".format(entry['uuid']))
        print("Database server: {}".format(entry['db_server']))
        print("Database port: {}".format(entry['db_port']))
        print("Number of database warehouses: {}".format(entry['db_warehouses']))
        print("Number of workers: {}".format(entry['db_num_workers']))
        print("TCP connection to the DB: {}".format(entry['db_tcp']))
        print("Database user: {}".format(entry['db_user']))
        print("Transactions: {}".format(entry['transactions']))
        print("Test type: {}".format(entry['test_type']))
        print("Runtime: {}".format(entry['runtime']))
        print("Rampup time: {}".format(entry['rampup']))
        print("Worker: {}".format(entry['worker']))
        print("Samples: {}".format(entry['samples']))
        print("Timed test: {}".format(entry['timed_test']))
        print("HammerDB results (TPM):")
        print("""
              TPM: {}""".format(entry['tpm']))
        print("HammerDB results (NOPM):")
        print("""
              NOPM: {}""".format(entry['nopm']))
        print("Timestamp: {}".format(entry['timestamp']))
        print("+{}+".format("-"*(115)))

def _index_result(index,es_server,es_port,payload):
    _es_connection_string = str(es_server) + ':' + str(es_port)
    es = elasticsearch.Elasticsearch([_es_connection_string],send_get_body_as='POST')
    indexed = True
    processed_count = 0
    total_count = 0
    for result in payload:
        try:
            es.index(index=index, body=result)
            processed_count += 1
        except Exception as e:
            print (repr(e) + "occured for the json document:")
            print(str(result))
            indexed = False
        total_count += 1
    return indexed, processed_count, total_count

def main():

    es_server = ""
    es_port = ""
    protocol = ""
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
    iteration = "" 
    test_type = ""
    timestamp = ""

    if "es_server" in os.environ:
        es_server = os.environ["es_server"]
    if "es_port" in os.environ:
        es_port = os.environ["es_port"]
    if "uuid" in os.environ:
        uuid = os.environ["uuid"]
    if "db_server" in os.environ:
        db_server = os.environ["db_server"]
    if "db_port" in os.environ:
        db_port = os.environ["db_port"]
    if "db_warehouses" in os.environ:
        db_warehouses = os.environ["db_warehouses"]
    if "db_num_workers" in os.environ:
        db_num_workers = os.environ["db_num_workers"]
    if "db_tcp" in os.environ:
        db_tcp = os.environ["db_tcp"]
    if "db_user" in os.environ:
        db_user = os.environ["db_user"]
    if "transactions" in os.environ:
        transactions = os.environ["transactions"]
    if "test_type" in os.environ:
        test_type = os.environ["test_type"]
    if "runtime" in os.environ:
        runtime = os.environ["runtime"]
    if "rampup" in os.environ:
        rampup = os.environ["rampup"]
    if "samples" in os.environ:
        samples = os.environ["samples"]
    if "timed_test" in os.environ:
        timed_test = os.environ["timed_test"]


    timestamp = str(int(time.time()))
    stdout = _run_hammerdb()
    #stdout = _fake_run()
    if stdout[1] == 1:
        print ("hammerdbcli failed to execute, trying one more time..")
        stdout = _run_hammerdb()
        if stdout[1] == 1:
            print ("hammerdbcli failed to execute a second time, stopping...")
            exit(1)
    data = _parse_stdout(stdout[0])
    documents = _json_payload(data, uuid, db_server, db_port, db_warehouses, db_num_workers, db_tcp, db_user, transactions, test_type, runtime, rampup, samples, timed_test, timestamp)
    if es_server != "" :
        if len(documents) > 0 :
            _index_result("ripsaw-hammerdb-results", es_server, es_port, documents)
    if len(documents) > 0 :
        _summarize_data(documents)


if __name__ == '__main__':
    sys.exit(main())
