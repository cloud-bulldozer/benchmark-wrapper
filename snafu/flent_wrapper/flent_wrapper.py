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

from .trigger_flent import Trigger_flent


class flent_wrapper:
    def __init__(self, parent_parser):
        parser_object = argparse.ArgumentParser(
            description="flent Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("flent benchmark")
        parser.add_argument(
            "-f", "--ftest", type=str, required=True, default="tcp_download", help="The test to run in Flent"
        )
        parser.add_argument(
            "-l",
            "--length",
            required=False,
            default="60",
            help="The duration of the test in seconds. Default 60 seconds",
        )
        parser.add_argument("-r", "--remoteip", required=True, help="The address of the netserver")
        parser.add_argument("-u", "--uuid", required=True, help="Provide the uuid")
        parser.add_argument("--user", required=True, default="snafu", help="Enter the user")

        self.args = parser_object.parse_args()

        self.args.server_node = os.getenv("server_node", "")
        self.args.client_node = os.getenv("client_node", "")
        self.args.cluster_name = os.getenv("clustername", "mycluster")

    def run(self):
        flent_wrapper_obj = Trigger_flent(self.args)
        yield flent_wrapper_obj
