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

from uperf_wrapper.trigger_uperf import Trigger_uperf


class uperf_wrapper():

    def __init__(self, parser):
        parser.add_argument(
            '-w', '--workload', nargs=1,
            help='Provide XML workload location')
        parser.add_argument(
            '-r', '--run', nargs=1,
            help='Provide the iteration for the run')
        parser.add_argument(
            '--resourcetype', nargs=1,
            help='Provide the resource type for this uperf run - pod/vm/baremetal')
        parser.add_argument(
            '-u', '--uuid', nargs=1,
            help='Provide the uuid')
        self.args = parser.parse_args()

        self.args.user = ""
        self.args.clientips = ""
        self.args.remoteip = ""
        self.args.hostnetwork = ""
        self.args.serviceip = ""
        self.args.server_node = ""
        self.args.client_node = ""
        self.args.cluster_name = "mycluster"

        if "clustername" in os.environ:
            self.args.cluster_name = os.environ["clustername"]
        if "serviceip" in os.environ:
            self.args.serviceip = os.environ['serviceip']
        if "test_user" in os.environ:
            self.args.user = os.environ["test_user"]
        if "hostnet" in os.environ:
            self.args.hostnetwork = os.environ["hostnet"]
        if "h" in os.environ:
            self.args.remoteip = os.environ["h"]
        if "ips" in os.environ:
            self.args.clientips = os.environ["ips"]
        if "server_node" in os.environ:
            self.args.server_node = os.environ["server_node"]
        if "client_node" in os.environ:
            self.args.client_node = os.environ["client_node"]

    def run(self):
        uperf_wrapper_obj = Trigger_uperf(self.args)
        yield uperf_wrapper_obj
