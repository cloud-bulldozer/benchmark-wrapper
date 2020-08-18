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
import argparse

from .trigger_uperf import Trigger_uperf


class uperf_wrapper():

    def __init__(self, parent_parser):
        parser_object = argparse.ArgumentParser(description="Uperf Wrapper script", parents=[parent_parser],
                                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser = parser_object.add_argument_group("Uperf benchmark")
        parser.add_argument(
            '-w', '--workload',
            help='Provide XML workload location', required=True)
        parser.add_argument(
            '-s', '--sample', type=int, required=True, default=1,
            help='Number of times to run the benchmark')
        parser.add_argument(
            '--resourcetype',
            required=True,
            help='Provide the resource type for this uperf run - pod/vm/baremetal')
        parser.add_argument(
            '-u', '--uuid',
            required=True,
            help='Provide the uuid')
        parser.add_argument(
            '--user',
            required=True,
            default="snafu",
            help='Enter the user')
        self.args = parser_object.parse_args()

        self.args.clientips = os.getenv("ips", "")
        self.args.remoteip = os.getenv("h", "")
        self.args.hostnetwork = os.getenv("hostnet", "")
        self.args.serviceip = os.getenv("serviceip", "")
        self.args.server_node = os.getenv("server_node", "")
        self.args.client_node = os.getenv("client_node", "")
        self.args.cluster_name = os.getenv("clustername", "mycluster")

    def run(self):
        uperf_wrapper_obj = Trigger_uperf(self.args)
        yield uperf_wrapper_obj
