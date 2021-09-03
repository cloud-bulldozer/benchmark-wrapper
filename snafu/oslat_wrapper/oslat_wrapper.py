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

import argparse
import os

from .trigger_oslat import Trigger_oslat


class oslat_wrapper:
    def __init__(self, parent_parser):
        parser_object = argparse.ArgumentParser(
            description="oslat Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("oslat benchmark")
        parser.add_argument("-p", "--path", required=True, help="Path to oslat script")
        parser.add_argument(
            "-s", "--samples", type=int, default=1, help="Number of times to run the benchmark"
        )
        parser.add_argument("-u", "--uuid", required=True, help="Provide the uuid")
        parser.add_argument("--user", default="snafu", help="Enter the user")
        self.args = parser_object.parse_args()

        self.args.duration = os.getenv("RUNTIME", "5m")
        self.args.disable_cpu_balance = os.getenv("DISABLE_CPU_BAlANCE", "true")
        self.args.use_taskset = os.getenv("USE_TASKSET", "true")
        self.args.cluster_name = os.getenv("clustername", "mycluster")

    def run(self):
        oslat_wrapper_obj = Trigger_oslat(self.args)
        yield oslat_wrapper_obj
