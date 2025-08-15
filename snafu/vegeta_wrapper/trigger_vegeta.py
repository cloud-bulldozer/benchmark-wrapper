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

import json
import logging
import os
import socket
import subprocess

import dateutil.parser

logger = logging.getLogger("snafu")


class Trigger_vegeta:
    def __init__(self, args):
        self.uuid = args.uuid
        self.user = args.user
        self.sample = args.sample
        self.workers = args.workers
        self.targets = args.targets
        self.duration = args.duration
        self.cluster_name = args.cluster_name
        self.keepalive = args.keepalive
        if args.results:
            self.target_name = args.target_name
            self.results = args.results
        else:
            self.results = None

    def _json_payload(self, data, sample):
        if self.results:
            targets = self.target_name
        else:
            targets = os.path.basename(self.targets)

        payload = {
            "workload": "vegeta",
            "uuid": self.uuid,
            "user": self.user,
            "cluster_name": self.cluster_name,
            "iteration": sample,
            "duration": self.duration,
            "workers": self.workers,
            "keepalive": self.keepalive,
            "targets": targets,
            "hostname": socket.gethostname(),
        }
        payload.update(data)
        return payload

    def _run_vegeta(self):
        cmd = (
            "vegeta attack -keepalive={0} -insecure -workers={1} -duration={2}s -targets={3} -rate=0"
            " -max-workers={1} | vegeta report --every=1s --type=json --output=vegeta.log"
        ).format(self.keepalive, self.workers, self.duration, self.targets)
        logger.info(cmd)
        p = subprocess.run(cmd, shell=True, capture_output=True)
        return p.stdout.strip().decode("utf-8"), p.stderr.strip().decode("utf-8"), p.returncode

    def _parse_stdout(self):
        status_codes = {}
        status_codes_bck = {}
        bytes_in_bck = 0
        bytes_out_bck = 0
        if self.results:
            vegeta_log = self.results
        else:
            vegeta_log = "vegeta.log"
        for line in open(vegeta_log).readlines():
            data = json.loads(line)
            rps = int(data["rate"])
            throughput = int(data["throughput"])
            for s, n in data["status_codes"].items():
                if s in status_codes_bck:
                    status_codes[s] = n - status_codes_bck[s]
                else:
                    status_codes[s] = n
                status_codes_bck[s] = n
            bytes_in = data["bytes_in"]["total"] - bytes_in_bck
            bytes_in_bck = data["bytes_in"]["total"]
            bytes_out = data["bytes_out"]["total"] - bytes_out_bck
            bytes_out_bck = data["bytes_out"]["total"]
            # Latency units are reported in nanoseconds. We convert them here to usecs
            p99 = int(data["latencies"]["99th"] / 1000)
            p95 = int(data["latencies"]["95th"] / 1000)
            ltcy = int(data["latencies"]["mean"] / 1000)
            max_ltcy = int(data["latencies"]["max"] / 1000)
            min_ltcy = int(data["latencies"]["min"] / 1000)
            ts = dateutil.parser.parse(data["end"])
            yield {
                "rps": rps,
                "throughput": throughput,
                "status_codes": status_codes,
                "requests": data["requests"],
                "p99_latency": p99,
                "p95_latency": p95,
                "max_latency": max_ltcy,
                "min_latency": min_ltcy,
                "req_latency": ltcy,
                "timestamp": ts,
                "bytes_in": bytes_in,
                "bytes_out": bytes_out,
            }

    def emit_actions(self):
        if self.results:
            for data in self._parse_stdout():
                es_data = self._json_payload(data, 1)
                yield es_data, "results"
        else:
            if not os.path.exists(self.targets):
                logger.critical("Targets file %s not found" % self.targets)
                exit(1)
            for s in range(1, self.sample + 1):
                logger.info("Starting vegeta sample %d out of %d with uuid %s" % (s, self.sample, self.uuid))
                stdout, stderr, rc = self._run_vegeta()
                if rc:
                    logger.critical("Vegeta failed with returncode %d, stopping benchmark" % rc)
                    logger.critical("stdout: %s" % stdout)
                    logger.critical("stderr: %s" % stderr)
                    exit(1)
                for data in self._parse_stdout():
                    es_data = self._json_payload(data, s)
                    yield es_data, "results"
                logger.info("Finished executing vegeta sample %d out of %d" % (s, self.sample))
