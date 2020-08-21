#!/usr/bin/env python

import os

from .trigger_hammerdb import Trigger_hammerdb


class hammerdb_wrapper():
    def __init__(self, parser):
        parser.add_argument(
            '-u', '--uuid', nargs=1,
            help='Provide the uuid')
        self.args = parser.parse_args()
        self.args.es_server = ""
        self.args.es_port = ""
        # generic benchmark parameters
        self.args.db_type = ""
        self.args.db_server = ""
        self.args.db_port = ""
        self.args.db_warehouses = ""
        self.args.db_num_workers = ""
        self.args.db_user = ""
        self.args.transactions = ""
        self.args.raiseerror = ""
        self.args.keyandthink = ""
        self.args.driver = ""
        self.args.rampup = ""
        self.args.runtime = ""
        self.args.allwarehouse = ""
        self.args.timeprofile = ""
        self.args.async_scale = ""
        self.args.async_client = ""
        self.args.async_verbose = ""
        self.args.async_delay = ""
        self.args.samples = ""
        # database specific parameters
        # mssql
        self.args.db_mssql_tcp = ""
        self.args.db_mssql_azure = ""
        self.args.db_mssql_authentication = ""
        self.args.db_mssql_linux_authent = ""
        self.args.db_mssql_odbc_driver = ""
        self.args.db_mssql_linux_odbc = ""
        self.args.db_mssql_imdb = ""
        self.args.db_mssql_bucket = ""
        self.args.db_mssql_durability = ""
        self.args.db_mssql_checkpoint = ""
        # mysql
        self.args.db_mysql_storage_engine = ""
        self.args.db_mysql_partition = ""
        # postgresql
        self.args.db_postgresql_superuser = ""
        self.args.db_postgresql_superuser_pass = ""
        self.args.db_postgresql_defaultdbase = ""
        self.args.db_postgresql_vacuum = ""
        self.args.db_postgresql_dritasnap = ""
        self.args.db_postgresql_oracompat = ""
        self.args.db_postgresql_storedprocs = ""

        # exporting the generic settings
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
        if "raiseerror" in os.environ:
            self.args.raiseerror = os.environ["raiseerror"]
        if "keyandthink" in os.environ:
            self.args.keyandthink = os.environ["keyandthink"]
        if "driver" in os.environ:
            self.args.driver = os.environ["driver"]
        if "rampup" in os.environ:
            self.args.rampup = os.environ["rampup"]
        if "runtime" in os.environ:
            self.args.runtime = os.environ["runtime"]
        if "allwarehouse" in os.environ:
            self.args.allwarehouse = os.environ["allwarehouse"]
        if "timeprofile" in os.environ:
            self.args.timeprofile = os.environ["timeprofile"]
        if "async_scale" in os.environ:
            self.args.async_scale = os.environ["async_scale"]
        if "async_client" in os.environ:
            self.args.async_client = os.environ["async_client"]
        if "async_verbose" in os.environ:
            self.args.async_verbose = os.environ["async_verbose"]
        if "async_delay" in os.environ:
            self.args.async_delay = os.environ["async_delay"]
        if "samples" in os.environ:
            self.args.samples = os.environ["samples"]
        # exporting db specific settings
        # mssql:
        if "db_mssql_tcp" in os.environ:
            self.args.db_mssql_tcp = os.environ["db_mssql_tcp"]
        if "db_mssql_azure" in os.environ:
            self.args.db_mssql_azure = os.environ["db_mssql_azure"]
        if "db_mssql_authentication" in os.environ:
            self.args.db_mssql_authtentication = os.environ["db_mssql_authentication"]
        if "db_mssql_linux_authent" in os.environ:
            self.args.db_mssql_linux_authent = os.environ["db_mssql_linux_authent"]
        if "db_mssql_odbc_driver" in os.environ:
            self.args.db_mssql_odbc_driver = os.environ["db_mssql_odbc_driver"]
        if "db_mssql_linux_odbc" in os.environ:
            self.args.db_mssql_linux_odbc = os.environ["db_mssql_linux_odbc"]
        if "db_mssql_imdb" in os.environ:
            self.args.db_mssql_imdb = os.environ["db_mssql_imdb"]
        if "db_mssql_bucket" in os.environ:
            self.args.db_mssql_bucket = os.environ["db_mssql_bucket"]
        if "db_mssql_durability" in os.environ:
            self.args.db_mssql_durability = os.environ["db_mssql_durability"]
        if "db_mssql_checkpoint" in os.environ:
            self.args.db_mssql_checkpoint = os.environ["db_mssql_checkpoint"]
        # mysql:
        if "db_mysql_storage_engine" in os.environ:
            self.args.db_mysql_storage_engine = os.environ["db_mysql_storage_engine"]
        if "db_mysql_partition" in os.environ:
            self.args.db_mysql_partition = os.environ["db_mysql_partition"]
        # postgresql
        if "db_postgresql_superuser" in os.environ:
            self.args.db_postgresql_superuser = os.environ["db_postgresql_superuser"]
        if "db_postgresql_superuser_pass" in os.environ:
            self.args.db_postgresql_superuser_pass = os.environ["db_postgresql_superuser_pass"]
        if "db_postgresql_defaultdbase" in os.environ:
            self.args.db_postgresql_defaultdbase = os.environ["db_postgresql_defaultdbase"]
        if "db_postgresql_vacuum" in os.environ:
            self.args.db_postgresql_vacuum = os.environ["db_postgresql_vacuum"]
        if "db_postgresql_dritasnap" in os.environ:
            self.args.db_postgresql_dritasnap = os.environ["db_postgresql_dritasnap"]
        if "db_postgresql_oracompat" in os.environ:
            self.args.db_postgresql_oracompat = os.environ["db_postgresql_oracompat"]
        if "db_postgresql_storedprocs" in os.environ:
            self.args.db_postgresql_storedprocs = os.environ["db_postgresql_storedprocs"]

    def run(self):
        hammerdb_wrapper_obj = Trigger_hammerdb(self.args)
        yield hammerdb_wrapper_obj
