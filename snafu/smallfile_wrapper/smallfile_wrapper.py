#!/usr/bin/env python
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
import logging
import os

from . import trigger_smallfile

logger = logging.getLogger("snafu")


class smallfile_wrapper:
    def __init__(self, parser):
        # collect arguments

        # it is assumed that the parser was created using argparse and already knows
        # about the --tool option
        parser.add_argument(
            "-s", "--samples", type=int, help="number of times to run benchmark, defaults to 1", default=1
        )
        parser.add_argument("-T", "--top", help="directory to access files in")
        parser.add_argument(
            "-d", "--dir", help="output parent directory", default=os.path.dirname(os.getcwd())
        )
        parser.add_argument(
            "-o", "--operations", help="sequence of smallfile operation types to run", default="create"
        )
        parser.add_argument("-y", "--yaml-input-file", help="smallfile parameters passed via YAML input file")
        self.args = parser.parse_args()

        self.server = ""

        self.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.cluster_name = os.environ["clustername"]

        self.uuid = ""
        if "uuid" in os.environ:
            self.uuid = os.environ["uuid"]

        self.user = ""
        if "test_user" in os.environ:
            self.user = os.environ["test_user"]

        self.redis_host = os.environ["redis_host"] if "redis_host" in os.environ else None
        self.redis_timeout = os.environ["redis_timeout"] if "redis_timeout" in os.environ else 60
        self.redis_timeout_th = os.environ["redis_timeout_th"] if "redis_timeout_th" in os.environ else 25
        self.clients = os.environ["clients"] if "clients" in os.environ else 1
        if not self.args.top:
            raise SnafuSmfException("must supply directory where you access flies")  # noqa
        self.samples = self.args.samples
        self.working_dir = self.args.top
        self.result_dir = self.args.dir
        self.yaml_input_file = self.args.yaml_input_file
        self.operations = self.args.operations

    def run(self):
        if not os.path.exists(self.result_dir):
            os.mkdir(self.result_dir)
        for s in range(1, self.samples + 1):
            sample_dir = self.result_dir + "/" + str(s)
            if not os.path.exists(sample_dir):
                os.mkdir(sample_dir)
            for o in self.operations.split(","):
                trigger_generator = trigger_smallfile._trigger_smallfile(
                    logger,
                    o,
                    self.yaml_input_file,
                    self.cluster_name,
                    self.working_dir,
                    sample_dir,
                    self.user,
                    self.uuid,
                    self.redis_host,
                    self.redis_timeout,
                    self.redis_timeout_th,
                    self.clients,
                    s,
                )
                yield trigger_generator
