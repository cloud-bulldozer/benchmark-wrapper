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
import subprocess
import time

from ttp import ttp

logger = logging.getLogger("snafu")


class Trigger_dns_perf:
    def __init__(self, args):
        """Initialize the arguments defined"""

        self.uuid = args.uuid
        self.cluster_name = args.cluster_name
        self.server_address = args.server_address
        self.queries_per_second = args.queries_per_second
        self.run_time = args.run_time
        self.data_file = args.data_file
        self.clients = args.clients

    def _json_payload(self, data, timestamp, elapsed_time):
        """Generates a json payload with the metrics of interest.
        This is the results document, it gets updated with metrics from the dns-perf run.
        """

        payload = {
            "uuid": self.uuid,
            "cluster_name": self.cluster_name,
            "clients": self.clients,
            "timestamp": timestamp,
            "elapsed_time": elapsed_time,
        }
        try:
            payload.update(data)
        except Exception as e:
            logging.error("Failed to update the result document, error: %s" % (e))
        return payload

    def run(self):
        """Runs dns-perf workload and returns the stdout"""

        command = "dnsperf -l {} -s {} -Q {} -d {} -c {}".format(
            self.run_time, self.server_address, self.queries_per_second, self.data_file, self.clients
        )
        logger.info(command)
        out = subprocess.Popen(
            command, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        (output, err) = out.communicate()
        if out.returncode != 0:
            logger.error(f"Failed to run {command}, error: {err}")
            exit(1)
        logger.info(f"Raw result: \n{output}")
        return output

    def _parse_stdout(self, stdout):
        """Parses the dns-perf run stdout.
        ttp template to parse the dns-perf stdout.
        """

        template = """
DNS Performance Testing Tool
Version {{ dnsperf_version }}

[Status] Command line: {{ command }}
[Status] Sending queries (to {{ dns_address }})
[Status] Started at: {{ start_timestamp }}
[Status] Stopping after {{ stop_time_duration | to_float }} seconds
[Status] Testing complete (time limit)

Statistics:

  Queries sent:         {{ queries_sent | to_int }}
  Queries completed:    {{ queries_completed | to_int }} ({{ queries_completed_percentage | to_float }}%)
  Queries lost:         {{ queries_lost | to_int }} ({{ queries_lost_percentage | to_float }}%)

  Response codes:       {{ response_code | to_int }}
  Average packet size:  request {{ avg_request_packet_size | to_int }}, response {{ avg_response_packet_size | to_int }} # noqa
  Run time (s):         {{ runtime | to_float }}
  Queries per second:   {{ QPS | to_float }}

  Average Latency (s):  {{ avg_latency | to_float }} (min {{ latency_min | to_float }}, max {{latency_max | to_float }}) # noqa
  Latency StdDev (s):   {{ latency_stddev | to_float }}
        """
        parser = ttp(stdout, template)
        try:
            parser.parse()
        except Exception as e:
            logger.error("Failed to parse dns-perf sdout, error: %s" % (e))
            exit(1)
        parsed_results = parser.result()[0][0]
        logger.info("Parsed results:")
        logger.info(parsed_results)
        return parsed_results

    def emit_actions(self):
        logger.info("Running dnsperf workload")
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        start_time = time.time()
        out = self.run()
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Elapsed time in seconds: {elapsed_time}")
        logger.info("Starting output parsing")
        try:
            data = self._parse_stdout(str(out))
            result_document = self._json_payload(data, timestamp, elapsed_time)
            yield result_document, "results"
        except Exception as e:
            logger.error("Failed to generate results document, error: %s" % (e))
            exit(1)
        logger.info("Successfully finished running dns-perf workload")
