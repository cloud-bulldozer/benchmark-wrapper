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
from uperf_wrapper import trigger_uperf

class uperf_wrapper():

    def __init__(self, parser):
        #parser = argparse.ArgumentParser(description="UPerf Wrapper script")
        parser.add_argument(
            '-w', '--workload', nargs=1,
            help='Provide XML workload location')
        parser.add_argument(
            '-r', '--run', nargs=1,
            help='Provide the iteration for the run')
        self.args = parser.parse_known_args()
    
        server = ""
        uuid = ""
        user = ""
        clientips = ""
        remoteip = ""
        hostnetwork = ""
        serviceip = ""
        self.args.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.args.cluster_name = os.environ["clustername"]
        if "serviceip" in os.environ:
            self.args.serviceip = os.environ['serviceip']
        if "uuid" in os.environ :
            #server = os.environ["es"]
            #port = os.environ["es_port"]
            self.args.uuid = os.environ["uuid"]
        if "test_user" in os.environ :
            self.args.user = os.environ["test_user"]
        if "hostnet" in os.environ:
            self.args.hostnetwork = os.environ["hostnet"]
        if "h" in os.environ:
            self.args.remoteip = os.environ["h"]
        if "ips" in os.environ:
            self.args.clientips = os.environ["ips"]
    
    def run(self):
        
        trigger_uperf_generator = trigger_uperf._trigger_uperf(self.args)
        
        yield trigger_uperf_generator