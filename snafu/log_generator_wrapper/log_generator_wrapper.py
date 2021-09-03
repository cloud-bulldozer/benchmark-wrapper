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

from .trigger_log_generator import Trigger_log_generator


class log_generator_wrapper:
    def __init__(self, parent_parser):
        parser_object = argparse.ArgumentParser(
            description="Log Generator Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("Log Generator")
        parser.add_argument("-u", "--uuid", required=True, help="Provide the uuid")
        parser.add_argument("--size", type=int, required=True, help="Size in bytes of a message")
        parser.add_argument("--messages-per-minute", type=int, help="How many messages to send in one minute")
        parser.add_argument("--messages-per-second", type=int, help="How many messages to send in one second")
        parser.add_argument(
            "--duration", type=int, required=True, help="How long to run the test for in minutes"
        )
        parser.add_argument("--user", default="snafu", help="Enter the user")
        parser.add_argument(
            "--pod-count", type=int, default=1, help="Total number of log generator pods to run"
        )
        parser.add_argument("--pod-name", default=None, help="Pod Name of log generator")
        parser.add_argument("--namespace", default=None, help="Namespace log generator lives in")
        parser.add_argument(
            "--timeout",
            type=int,
            default=600,
            help="Max amount of time (in seconds) to wait for the backend service\
                  to obtain all the logs once the test is complete",
        )
        parser.add_argument("--cloudwatch-log-group", help="The cloudwatch log group to check for messages")
        parser.add_argument(
            "--aws-access-key", default=None, help="AWS access key id used for verification with cloudwatch"
        )
        parser.add_argument(
            "--aws-secret-key", default=None, help="AWS secret key used for verification with cloudwatch"
        )
        parser.add_argument("--aws-region", default=None, help="AWS region that CloudWatch is in")
        parser.add_argument("--es-url", help="Provide elastic server url")
        parser.add_argument("--es-token", help="Bearer token to access ES server")
        parser.add_argument(
            "--es-index", type=str, default="app*", help="The ES index to search for the messages"
        )
        parser.add_argument("--kafka-bootstrap-server", help="The Kafka Service to connect to")
        parser.add_argument("--kafka-topic", help="The Kafka topic to verify logs")
        parser.add_argument("--kafka-check", help="Verify if logs made it to kafka sink", action="store_true")
        self.args = parser_object.parse_args()

        self.args.cluster_name = os.getenv("clustername", "mycluster")

    def run(self):
        yield Trigger_log_generator(self.args)
