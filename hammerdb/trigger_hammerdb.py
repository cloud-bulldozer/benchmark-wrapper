#!/usr/bin/env python

import subprocess
import time
import logging

logger = logging.getLogger("snafu")

class Trigger_hammerdb():
    def __init__(self, args):
        self.uuid = args.uuid
        self.db_type = args.db_type
        self.db_server = args.db_server
        self.db_port = args.db_port
        self.db_warehouses = args.db_warehouses
        self.db_num_workers = args.db_num_workers
        self.db_mssql_tcp = args.db_mssql_tcp
        self.db_user = args.db_user
        self.transactions = args.transactions
        self.test_type = args.test_type
        self.runtime = args.runtime
        self.rampup = args.rampup
        self.samples = args.samples

    def _run_hammerdb(self):
        cmd = "cd /hammer; ./hammerdbcli auto /workload/tpcc-workload-"+self.db_type+".tcl"
        logger.info(cmd)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), process.returncode

    def _fake_run(self):
        with open("hammerdb.log", "r") as input:
            stdout = input.read()
        return stdout, 0

    def _parse_stdout(self, stdout):
        logger.info("parsing stdout")
        data = []
        for line in stdout.splitlines():
            logger.info(line)
            if "TEST RESULT" in line:
                worker = (line.split(":"))[0]
                tpm = (line.split(" "))[6]
                nopm = (line.split(" "))[-2]
                entry = [worker, tpm, nopm]
                data.append(entry)
        return data

    def _json_payload(self, data, uuid, db_server, db_port, db_warehouses, db_num_workers, db_mssql_tcp,
                      db_user,
                      transactions, test_type, runtime, rampup, samples, timestamp):
        logger.info("generating json payload")
        processed = []
        for current_worker in range(0, int(db_num_workers)):
            for current_sample in range(0, int(samples)):
                for i in range(0, len(data)):
                    processed.append({
                        "workload": "hammerdb",
                        "uuid": uuid,
                        "db_server": db_server,
                        "db_port": db_port,
                        "db_warehouses": db_warehouses,
                        "db_num_workers": db_num_workers,
                        "db_mssql_tcp": db_mssql_tcp,
                        "db_user": db_user,
                        "transactions": transactions,
                        "test_type": test_type,
                        "runtime": runtime,
                        "rampup": rampup,
                        "samples": samples,
                        "current_sample": current_sample,
                        "current_worker": current_worker,
                        "worker": data[i][0],
                        "tpm": data[i][1],
                        "nopm": data[i][2],
                        "timestamp": timestamp
                    })
        return processed

    def _summarize_data(self, data):
        logger.info("summarizing data")
        max_workers = int(data[0]['db_num_workers'])
        max_samples = int(data[0]['samples'])
        for current_worker in range(0, max_workers):
            for current_sample in range(0, max_samples):
                for i in range(0, len(data)):
                    entry = data[i]
                    print("+{} HammerDB Results {}+".format("-" * (50), "-" * (50)))
                    print("HammerDB setup")
                    print("")
                    print("HammerDB results for:")
                    print("UUID: {}".format(entry['uuid']))
                    print("Database server: {}".format(entry['db_server']))
                    print("Database port: {}".format(entry['db_port']))
                    print("Number of database warehouses: {}".format(entry['db_warehouses']))
                    print("Number of workers: {}".format(entry['db_num_workers']))
                    print("TCP connection to the DB: {}".format(entry['db_mssql_tcp']))
                    print("Database user: {}".format(entry['db_user']))
                    print("Transactions: {}".format(entry['transactions']))
                    print("Test type: {}".format(entry['test_type']))
                    print("Runtime: {}".format(entry['runtime']))
                    print("Rampup time: {}".format(entry['rampup']))
                    print("Worker: {}".format(current_worker))
                    print("Samples: {}".format(entry['samples']))
                    print("Current sample {}".format(current_sample))
                    print("HammerDB results (TPM):")
                    print("""
                          TPM: {}""".format(entry['tpm']))
                    print("HammerDB results (NOPM):")
                    print("""
                          NOPM: {}""".format(entry['nopm']))
                    print("Timestamp: {}".format(entry['timestamp']))
                    print("+{}+".format("-" * (115)))

    def emit_actions(self):
        timestamp = str(int(time.time()))
        logger.info("Starting hammerdb run")
        stdout = self._run_hammerdb()
        # stdout = _fake_run()
        if stdout[1] == 1:
            print("hammerdbcli failed to execute, trying one more time..")
            stdout = self._run_hammerdb()
            if stdout[1] == 1:
                print("hammerdbcli failed to execute a second time, stopping...")
                exit(1)
        data = self._parse_stdout(stdout[0])
        documents = self._json_payload(data, self.uuid, self.db_server, self.db_port,
                                       self.db_warehouses, self.db_num_workers, self.mssql_db_tcp,
                                       self.db_user, self.transactions, self.test_type,
                                       self.runtime, self.rampup, self.samples,
                                       timestamp)
        logger.info(documents)
        if len(documents) > 0:
            self._summarize_data(documents)
        if len(documents) > 0:
            for document in documents:
                yield document, 'results'
        else:
            raise Exception('Failed to produce hammerdb results document')
