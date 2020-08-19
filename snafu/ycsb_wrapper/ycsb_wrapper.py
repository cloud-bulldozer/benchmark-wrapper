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

from .trigger_ycsb import Trigger_ycsb


class ycsb_wrapper():

    def __init__(self, parser):
        parser.add_argument(
            '-r', '--run', nargs=1,
            help='Provide the iteration for the run')
        parser.add_argument(
            '-l', '--load', action='store_true', default=False,
            help='Run the load phase?')
        parser.add_argument(
            '-d', '--driver', nargs=1,
            help='Which YCSB Driver, eg mongodb')
        parser.add_argument(
            '-w', '--workload', nargs=1,
            help='Which YCSB workload, eg workloada')
        parser.add_argument(
            '-x', '--extra', nargs=1,
            help='Extra params to pass')
        parser.add_argument(
            '-u', '--uuid', nargs=1,
            help='Enter the uuid')
        parser.add_argument(
            '--user', nargs=1,
            help='Enter the user')

        self.args = parser.parse_args()
        if self.args.driver is None:
            parser.print_help()
            exit(1)

        self.args.recordcount = ""
        self.args.operationcount = ""
        self.args.phase = ""
        self.args.port = ""
        self.args.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.args.cluster_name = os.environ["clustername"]
        if "workload" in os.environ:
            self.args.workload = os.environ["workload"]
        if "num_records" in os.environ:
            self.args.recordcount = os.environ["num_records"]
        if "num_operations" in os.environ:
            self.args.operationcount = os.environ["num_operations"]

    def run(self):
        ycsb_wrapper_obj = Trigger_ycsb(self.args)
        yield ycsb_wrapper_obj
