#!/usr/bin/env python3

import datetime
import logging
import subprocess

logger = logging.getLogger("snafu")


class Trigger_hammerdb:
    def __init__(self, args):
        self.uuid = args.uuid
        # generic arguments
        self.db_type = args.db_type
        self.db_server = args.db_server
        self.db_port = args.db_port
        self.db_warehouses = args.db_warehouses
        self.db_num_workers = args.db_num_workers
        self.db_user = args.db_user
        self.transactions = args.transactions
        self.raiseerror = args.raiseerror
        self.keyandthink = args.keyandthink
        self.driver = args.driver
        self.runtime = args.runtime
        self.rampup = args.rampup
        self.allwarehouse = args.allwarehouse
        self.timeprofile = args.timeprofile
        self.async_scale = args.async_scale
        self.async_client = args.async_client
        self.async_verbose = args.async_verbose
        self.async_delay = args.async_delay
        self.samples = args.samples
        # db specific arguments
        # mssql
        self.db_mssql_tcp = args.db_mssql_tcp
        self.db_mssql_azure = args.db_mssql_azure
        self.db_mssql_authentication = args.db_mssql_authentication
        self.db_mssql_linux_authent = args.db_mssql_linux_authent
        self.db_mssql_odbc_driver = args.db_mssql_odbc_driver
        self.db_mssql_linux_odbc = args.db_mssql_linux_odbc
        self.db_mssql_imdb = args.db_mssql_imdb
        self.db_mssql_bucket = args.db_mssql_bucket
        self.db_mssql_durability = args.db_mssql_durability
        self.db_mssql_checkpoint = args.db_mssql_checkpoint
        # mysql
        self.db_mysql_storage_engine = args.db_mysql_storage_engine
        self.db_mysql_partition = args.db_mysql_partition
        # postgresql
        self.db_postgresql_superuser = args.db_postgresql_superuser
        self.db_postgresql_defaultdbase = args.db_postgresql_defaultdbase
        self.db_postgresql_vacuum = args.db_postgresql_vacuum
        self.db_postgresql_dritasnap = args.db_postgresql_dritasnap
        self.db_postgresql_oracompat = args.db_postgresql_oracompat
        self.db_postgresql_storedprocs = args.db_postgresql_storedprocs
        # es customs fields
        self.es_ocp_version = args.es_ocp_version
        self.es_cnv_version = args.es_cnv_version
        self.es_db_version = args.es_db_version
        self.es_os_version = args.es_os_version
        self.es_kind = args.es_kind

    def _pack_db_info(self):
        db_info = []
        if self.db_type == "mssql":
            db_info.append({"db_mssql_tcp": self.db_mssql_tcp})
            db_info.append({"db_mssql_azure": self.db_mssql_azure})
            db_info.append({"db_mssql_authentication": self.db_mssql_authentication})
            db_info.append({"db_mssql_linux_authent": self.db_mssql_linux_authent})
            db_info.append({"db_mssql_odbc_driver": self.db_mssql_odbc_driver})
            db_info.append({"db_mssql_linux_odbc": self.db_mssql_linux_odbc})
            db_info.append({"db_mssql_imdb": self.db_mssql_imdb})
            db_info.append({"db_mssql_bucket": self.db_mssql_bucket})
            db_info.append({"db_mssql_durability": self.db_mssql_durability})
            db_info.append({"db_mssql_checkpoint": self.db_mssql_checkpoint})
        if self.db_type == "mysql":
            db_info.append({"db_mysql_storage_engine": self.db_mysql_storage_engine})
            db_info.append({"db_mysql_partition": self.db_mysql_partition})
        if self.db_type == "pg":
            db_info.append({"db_postgresql_superuser": self.db_postgresql_superuser})
            db_info.append({"db_postgresql_defaultdbase": self.db_postgresql_defaultdbase})
            db_info.append({"db_postgresql_vacuum": self.db_postgresql_vacuum})
            db_info.append({"db_postgresql_dritasnap": self.db_postgresql_dritasnap})
            db_info.append({"db_postgresql_oracompat": self.db_postgresql_oracompat})
            db_info.append({"db_postgresql_storedprocs": self.db_postgresql_storedprocs})
        return db_info

    def _run_hammerdb(self):
        cmd = "cd /hammer; ./hammerdbcli auto /workload/tpcc-workload-" + self.db_type + ".tcl"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), process.returncode

    def _fake_run(self):
        with open("hammerdb.log") as input:
            stdout = input.read()
        return stdout, 0

    def _parse_stdout(self, stdout):
        logger.info("Parsing stdout")
        data = []
        for line in stdout.splitlines():
            if "TEST RESULT" in line:
                worker_name = (line.split())[1]
                worker = int((worker_name.split(":"))[0])
                if (line.split())[-3] == "SQL":  # MSSQL
                    tpm = int((line.split())[-4])
                    nopm = int((line.split())[-7])
                else:  # PostgreSQL, MySQL
                    tpm = int((line.split())[-3])
                    nopm = int((line.split())[-6])
                entry = [worker, tpm, nopm]
                data.append(entry)
        return data

    def _json_payload(
        self,
        data,
        uuid,
        db_type,
        db_server,
        db_port,
        db_warehouses,
        db_num_workers,
        db_user,
        transactions,
        runtime,
        rampup,
        samples,
        raiseerror,
        keyandthink,
        driver,
        allwarehouse,
        timeprofile,
        async_scale,
        async_client,
        async_verbose,
        async_delay,
        es_ocp_version,
        es_cnv_version,
        es_db_version,
        es_os_version,
        es_kind,
        timestamp,
    ):
        db_info = self._pack_db_info()
        logger.info("generating json payload")
        processed = []
        i = 0
        # for current_worker in range(0, int(self.db_num_workers)):
        current_worker = 1
        while current_worker <= (int(self.db_num_workers)):
            for current_sample in range(0, int(self.samples)):
                processed.append(
                    {
                        "workload": "hammerdb",
                        "uuid": uuid,
                        "db_type": db_type,
                        "db_server": db_server,
                        "db_port": db_port,
                        "db_warehouses": db_warehouses,
                        "db_num_workers": db_num_workers,
                        "db_user": db_user,
                        "transactions": transactions,
                        "runtime": runtime,
                        "rampup": rampup,
                        "raiseerror": raiseerror,
                        "keyandthink": keyandthink,
                        "driver": driver,
                        "allwarehouse": allwarehouse,
                        "timeprofile": timeprofile,
                        "async_scale": async_scale,
                        "async_client": async_client,
                        "async_verbose": async_verbose,
                        "async_delay": async_delay,
                        "samples": samples,
                        "current_sample": current_sample,
                        "current_worker": current_worker,
                        "worker": data[i][0],
                        "tpm": data[i][1],
                        "nopm": data[i][2],
                        "es_ocp_version": es_ocp_version,
                        "es_cnv_version": es_cnv_version,
                        "es_db_version": es_db_version,
                        "es_os_version": es_os_version,
                        "es_kind": es_kind,
                        "timestamp": timestamp,
                    }
                )
                i += 1
            current_worker *= 2

        # we need to add the db specific information to the processed list
        for item in db_info:
            for k, v in item.items():
                processed.append({k: v})
        return processed

    def _summarize_data(self, data):
        db_info = self._pack_db_info()
        i = 0
        # for current_worker in range(0, int(self.db_num_workers)):
        current_worker = 1
        while current_worker <= (int(self.db_num_workers)):
            for current_sample in range(0, int(self.samples)):
                entry = data[i]
                print("+{} HammerDB Results {}+".format("-" * (50), "-" * (50)))
                print("HammerDB setup")
                print("")
                print("HammerDB results for:")
                print("UUID: {}".format(entry["uuid"]))
                print("Database server: {}".format(entry["db_server"]))
                print("Database port: {}".format(entry["db_port"]))
                print("Number of database warehouses: {}".format(entry["db_warehouses"]))
                print("Max. number of workers: {}".format(entry["db_num_workers"]))
                print("Database user: {}".format(entry["db_user"]))
                print("Transactions: {}".format(entry["transactions"]))
                print("Test driver: {}".format(entry["driver"]))
                print("Runtime: {}".format(entry["runtime"]))
                print("Rampup time: {}".format(entry["rampup"]))
                print(f"Worker(s): {current_worker}")
                print("Total samples: {}".format(entry["samples"]))
                print(f"Current sample {current_sample + 1}")
                print("HammerDB results (TPM):")
                print(
                    """
                      TPM: {}""".format(
                        entry["tpm"]
                    )
                )
                print("HammerDB results (NOPM):")
                print(
                    """
                      NOPM: {}""".format(
                        entry["nopm"]
                    )
                )
                print("DB specific settings:")
                for item in db_info:
                    for k, v in item.items():
                        print(k + " : " + v)
                print("Timestamp: {}".format(entry["timestamp"]))
                print("+{}+".format("-" * (115)))
                i += 1
            current_worker *= 2

    def emit_actions(self):
        timestamp = datetime.datetime.utcnow()
        logger.info("Starting hammerdb run")
        stdout = self._run_hammerdb()
        if stdout[1] == 1:
            print("hammerdbcli failed to execute, trying one more time..")
            stdout = self._run_hammerdb()
            if stdout[1] == 1:
                print("hammerdbcli failed to execute a second time, stopping...")
                exit(1)
        data = self._parse_stdout(stdout[0])
        documents = self._json_payload(
            data,
            self.uuid,
            self.db_type,
            self.db_server,
            self.db_port,
            self.db_warehouses,
            self.db_num_workers,
            self.db_user,
            self.transactions,
            self.runtime,
            self.rampup,
            self.samples,
            self.raiseerror,
            self.keyandthink,
            self.driver,
            self.allwarehouse,
            self.timeprofile,
            self.async_scale,
            self.async_client,
            self.async_verbose,
            self.async_delay,
            self.es_ocp_version,
            self.es_cnv_version,
            self.es_db_version,
            self.es_os_version,
            self.es_kind,
            timestamp,
        )
        if len(documents) > 0:
            self._summarize_data(documents)
        if len(documents) > 0:
            for document in documents:
                yield document, "results"
        else:
            raise Exception("Failed to produce hammerdb results document")
