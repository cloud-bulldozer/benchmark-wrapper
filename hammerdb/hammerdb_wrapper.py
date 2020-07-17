#!/usr/bin/env python

import os

from hammerdb.trigger_hammerdb import Trigger_hammerdb


class hammerdb_wrapper():
    def __init__(self, parser):
        parser.add_argument(
            '-u', '--uuid', nargs=1,
            help='Provide the uuid')
        self.args = parser.parse_args()
        self.args.es_server = ""
        self.args.es_port = ""
        self.args.db_user = ""
        self.args.db_server = ""
        self.args.db_port = ""
        self.args.db_warehouses = ""
        self.args.db_num_workers = ""
        self.args.transactions = ""
        self.args.runtime = ""
        self.args.rampup = ""
        self.args.samples = ""
        self.args.test_type = ""
        self.args.timestamp = ""
        self.args.db_tcp = ""
        self.args.timed_test = ""

        if "es_server" in os.environ:
            self.args.es_server = os.environ["es_server"]
        if "es_port" in os.environ:
            self.args.es_port = os.environ["es_port"]
        if "db_type" in os.environ:
            self.args.db_type = os.environ["db_type"]
        if "db_server" in os.environ:
            self.args.db_server = os.environ["db_server"]
        if "db_port" in os.environ:
            self.args.db_port = os.environ["db_port"]
        if "db_warehouses" in os.environ:
            self.args.db_warehouses = os.environ["db_warehouses"]
        if "db_num_workers" in os.environ:
            self.args.db_num_workers = os.environ["db_num_workers"]
        if "db_user" in os.environ:
            self.args.db_user = os.environ["db_user"]
        if "transactions" in os.environ:
            self.args.transactions = os.environ["transactions"]
        if "test_type" in os.environ:
            self.args.test_type = os.environ["test_type"]
        if "runtime" in os.environ:
            self.args.runtime = os.environ["runtime"]
        if "rampup" in os.environ:
            self.args.rampup = os.environ["rampup"]
        if "samples" in os.environ:
            self.args.samples = os.environ["samples"]
        if "timed_test" in os.environ:
            self.args.timed_test = os.environ["timed_test"]
        # db specific settings
        # mssql:
        if "db_mssql_tcp" in os.environ:
            self.args.db_mssql_tcp = os.environ["db_mssql_tcp"]
        # mysql:
        if "db_mysql_tse" in os.environ:
            self.args.db_mysql_tse = os.environ["db_mysql_tse"]
        # postgresql
        if "db_postgresql_default_db" in os.environ:
            self.args.db_postgresql_default_db = os.environ["db_postgresql_default_db"]
        if "db_postgresql_oracle_compat" in os.environ:
            self.args.db_postgresql_oracle_compat = os.environ["db_postgresql_oracle_compat"]
        if "db_postgresql_stored_procedures" in os.environ:
            self.args.db_postgresql_stored_procedures = os.environ["db_postgresql_stored_procedures"]
        if "db_postgresql_superuser" in os.environ:
            self.args.db_postgresql_superuser = os.environ["db_postgresql_superuser"]
        if "db_postgresql_superuser_pass" in os.environ:
            self.args.db_postgresql_superuser_pass = os.environ["db_postgresql_superuser_pass"]

    def run(self):
        hammerdb_wrapper_obj = Trigger_hammerdb(self.args)
        yield hammerdb_wrapper_obj
