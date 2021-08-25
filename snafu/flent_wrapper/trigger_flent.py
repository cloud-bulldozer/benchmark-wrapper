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

import gzip
import json
import logging
import re
import subprocess
from datetime import datetime, timedelta

from dateutil import parser

logger = logging.getLogger("snafu")


class Trigger_flent:
    def __init__(self, args):
        self.ftest = args.ftest
        self.remoteip = args.remoteip
        self.length = args.length
        self.server_node = args.server_node
        self.client_node = args.client_node
        self.cluster_name = args.cluster_name
        self.uuid = args.uuid

    def _json_payload(self, raw):
        processed = []
        # Useful reference: https://flent.org/data-format.html
        results = raw["results"]
        start_time = parser.isoparse(raw["metadata"]["TIME"])
        times = raw["x_values"]
        # There is an unknown quantity (usually 2 or 3) of
        # dictionaries in results. They contain the same number
        # of items, and are in parallel.
        # This code will convert the parallel arrays to items
        # with each of those.

        keys = list(results.keys())

        quantity = len(results[keys[0]])
        logger.info("Number of results: %s", quantity)

        for i in range(0, quantity):
            new_results_item = {}
            for key in keys:
                new_results_item[key] = results[key][i]
            new_item = self._json_result(
                "results", new_results_item, start_time + timedelta(seconds=times[i])
            )
            processed.append(new_item)

        return processed

    def _json_result(self, name, value, time):
        new_item = {
            "workload": "flent",
            "test_type": self.ftest,
            "remote_ip": self.remoteip,
            "client_node": self.client_node,
            "server_node": self.server_node,
            "timestamp": time,
            "uuid": self.uuid,
            name: value,
        }
        return new_item

    def _run_flent(self):
        cmd = "flent {} -p totals -l {} -f summary -H {} --absolute-time".format(
            self.ftest, self.length, self.remoteip
        )
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), stderr.strip().decode("utf-8"), process.returncode

    def _parse_stdout(self, stdout):
        # This is set to summary output, so process that.
        # And open the raw file for the data.
        print("Stdout:", stdout)
        search_results = re.search("Data file written to (\\./.+.gz)(.+)", stdout, re.DOTALL)
        file_name = search_results[1]
        raw = {}
        logger.info("Opening results file %s", file_name)
        with gzip.open(file_name, "rb") as f:
            raw = json.load(f)
        summary = search_results[2]
        return raw, summary

    def emit_actions(self):
        logger.info("Starting flent benchmark")
        stdout, stderr, rc = self._run_flent()
        if rc != 0 or stderr.find("ERROR") != -1:
            logger.critical("Failed to execute flent. Error in output.")
            logger.critical("stdout: %s", stdout)
            logger.critical("stderr: %s", stderr)
            exit(1)

        raw, summary = self._parse_stdout(stdout)
        yield self._json_result("raw", raw, datetime.now()), "raw"
        documents = self._json_payload(raw)
        if len(documents) > 0:
            for document in documents:
                yield document, "results"
        logger.info(stdout)
        logger.info("Finished executing flent")
