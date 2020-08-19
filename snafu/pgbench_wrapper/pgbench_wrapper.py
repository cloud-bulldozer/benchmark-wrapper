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

import os
import subprocess
from datetime import datetime

from .trigger_pgbench import Trigger_pgbench


class pgbench_wrapper():
    def __init__(self, parser):
        parser.add_argument(
            '-r', '--run', nargs=1,
            help='Provide the iteration for the run')
        self.args = parser.parse_args()

        self.args.port = ""
        self.args.uuid = ""
        self.args.user = ""
        self.args.database = ""
        self.args.description = ""
        self.args.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.args.cluster_name = os.environ["clustername"]
        self.args.pgb_vers = subprocess.check_output("pgbench --version",
                                                     shell=True).strip().decode("utf-8")
        self.args.run_start_timestamp = datetime.now()
        self.args.sample_start_timestamp = datetime.now()
        self.args.index = "ripsaw-pgbench"

        if "uuid" in os.environ:
            self.args.uuid = os.environ["uuid"]
        if "test_user" in os.environ:
            self.args.user = os.environ["test_user"]
        if "database" in os.environ:
            self.args.database = os.environ["database"]
        if "description" in os.environ:
            self.args.description = os.environ["description"]
        if "run_start_timestamp" in os.environ:
            self.args.run_start_timestamp = datetime.fromtimestamp(
                float(os.environ["run_start_timestamp"]))
        if "sample_start_timestamp" in os.environ:
            self.args.sample_start_timestamp = datetime.fromtimestamp(
                float(os.environ["sample_start_timestamp"]))

    def run(self):
        pgbench_wrapper_obj = Trigger_pgbench(self.args)
        yield pgbench_wrapper_obj
