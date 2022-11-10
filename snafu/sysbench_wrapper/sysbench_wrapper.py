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

import logging
import os
import time
import uuid

from . import trigger_sysbench

logger = logging.getLogger("snafu")


class sysbench_wrapper:
    def __init__(self, parser):

        # it is assumed that the parser was created using argparse and already knows
        # about the initial --tool option
        parser.add_argument(
            "-f", "--file", default="", help="sysbench test file containing benchmark parameters"
        )
        parser.add_argument(
            "-s", "--sample", type=int, default=1, help="number of times to run benchmark, defaults to 1"
        )
        parser.add_argument(
            "-d",
            "--delay",
            type=int,
            default=0,
            help="add delay(seconds) in between samples, defaults to 0",
        )
        parser.add_argument("--args", default="", help="arguments to pass to sysbench with --test flag")

        self.args = parser.parse_args()

        self.args.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.args.cluster_name = os.environ["clustername"]

        self.uuid = os.getenv("uuid", str(uuid.uuid4()))
        self.user = os.getenv("test_user", "myuser")
        self.delay = self.args.delay
        self.samples = self.args.sample
        self.sysbench_args = self.args.args

    def run(self):

        # Execute sysbench for X number of samples, yield the trigger_sysbench_generator
        for sample in range(1, self.samples + 1):

            trigger_sysbench_generator = trigger_sysbench.trigger_sysbench(
                self.uuid, self.user, self.args.cluster_name, self.args.file, sample, self.sysbench_args
            )

            yield trigger_sysbench_generator
            logger.info("delaying for %s seconds." % self.delay)
            time.sleep(self.delay)
