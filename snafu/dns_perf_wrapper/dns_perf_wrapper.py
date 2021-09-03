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

from .trigger_dns_perf import Trigger_dns_perf


class dns_perf_wrapper:
    def __init__(self, parent_parser):
        """Initialize supported arguments"""

        parser_object = argparse.ArgumentParser(
            description="DNS perf workload Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("DNS Perf")
        parser.add_argument("-u", "--uuid", required=True, help="Provide the uuid")
        parser.add_argument("--server-address", required=True, help="DNS server address to send the requests")
        parser.add_argument(
            "--queries-per-second", required=True, type=int, help="Number of queries per second"
        )
        parser.add_argument("--run-time", type=int, required=True, help="run for at most this many seconds")
        parser.add_argument(
            "--data-file", required=True, help="File path with the records to send as queries to the server"
        )
        parser.add_argument("--clients", default=1, help="The number of clients to act as")

        self.args = parser_object.parse_args()

        self.args.cluster_name = os.getenv("clustername", "mycluster")

    def run(self):
        yield Trigger_dns_perf(self.args)
