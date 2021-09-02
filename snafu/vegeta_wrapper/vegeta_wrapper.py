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

from .trigger_vegeta import Trigger_vegeta


class vegeta_wrapper:
    def __init__(self, parent_parser):
        parser_object = argparse.ArgumentParser(
            description="Vegeta Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("Vegeta benchmark")
        parser.add_argument("--targets", required=False, help="Targets file in http format")
        parser.add_argument(
            "--target_name",
            required=False,
            help="Name of the target hit attacked. Note: only used when -r is passed.",
        )
        parser.add_argument(
            "-w", "--workers", default=1, type=int, help="Provide the number of workers for vegeta"
        )
        parser.add_argument("-u", "--uuid", required=True, help="Provide the uuid")
        parser.add_argument(
            "-d", "--duration", default="30", type=int, help="Provide the duration of the test in seconds"
        )
        parser.add_argument("--user", default="snafu", help="Enter the user")
        parser.add_argument("--keepalive", action="store_true", help="Use TCP keep-alive")
        parser.add_argument(
            "-s", "--sample", type=int, default=1, help="Number of times to run the benchmark"
        )
        parser.add_argument("-r", "--results", required=False, help="Load Vegeta result file")
        self.args = parser_object.parse_args()

        self.args.cluster_name = os.getenv("clustername", "mycluster")

    def run(self):
        yield Trigger_vegeta(self.args)
