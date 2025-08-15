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

import re
import subprocess
from datetime import datetime


class Trigger_ycsb:
    def __init__(self, args):
        self.uuid = args.uuid
        self.user = args.user
        self.workload = args.workload
        self.recordcount = args.recordcount
        self.operationcount = args.operationcount
        self.phase = args.phase
        self.cluster_name = args.cluster_name
        self.port = args.port
        self.extra = args.extra
        self.load = args.load
        self.driver = args.driver
        self.run = args.run

    def _run(self, cmd):
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), stderr.strip().decode("utf-8"), process.returncode

    def _json_payload(
        self, data, iteration, uuid, user, phase, workload, driver, recordcount, operationcount, clustername
    ):
        processed = []
        summary = []
        for result in data["results"]:
            for action in result[3].split("["):
                bits = action.split(" ")
                if len(bits) < 2:
                    continue
                if bits[0][len(bits[0]) - 1] != ":":
                    continue
                _date = result[0].split(" ")[0].split("-")
                _time = result[0].split(" ")[1].split(":")
                if len(bits) >= 8:
                    processed.append(
                        {
                            "workload": "ycsb",
                            "uuid": uuid,
                            "user": user,
                            "cluster_name": clustername,
                            "phase": phase,
                            "driver": driver,
                            "timestamp": datetime(
                                int(_date[0]),
                                int(_date[1]),
                                int(_date[2]),
                                int(_time[0]),
                                int(_time[1]),
                                int(_time[2]),
                                int(_time[3]),
                            ),
                            "overall_rate": float(result[2].split(" ")[0]),
                            "action": bits[0][:-1],
                            "count": int(bits[1].split("=")[1][:-1]),
                            "latency_90": int(bits[5].split("=")[1][:-1]),
                            "latency_min": int(bits[3].split("=")[1][:-1]),
                            "latency_max": int(bits[2].split("=")[1][:-1]),
                            "recordcount": int(recordcount),
                            "operationcount": int(operationcount),
                            "iteration": int(iteration),
                            "workload_type": workload,
                        }
                    )
        summary_dict = {}
        if "summary" in data:
            for summ in data["summary"]:
                if summ[0][0].isdigit() or summ[0][0] == "I":
                    continue
                if not summ[0].strip("[").strip("]") in summary_dict:
                    summary_dict[summ[0].strip("[").strip("]")] = {}
                summary_dict[summ[0].strip("[").strip("]")][summ[1]] = float(summ[2])
            summary.append(
                {
                    "workload": "ycsb",
                    "uuid": uuid,
                    "user": user,
                    "phase": phase,
                    "driver": driver,
                    "timestamp": datetime.now(),
                    "data": summary_dict,
                    "recordcount": int(recordcount),
                    "operationcount": int(operationcount),
                    "iteration": int(iteration),
                    "workload_type": workload,
                }
            )
        return processed, summary

    def _parse_stdout(self, data):
        data_points = re.findall(
            r"(\d+-\d+-\d+ \d+:\d+:\d+:\d+) \d+ sec: (\d+ operations); (\d+.\d+? current ops/sec); (.*)", data
        )
        summary = re.findall(r"(.*), (.*), (.*)", data)
        return {"results": data_points, "summary": summary}

    def emit_actions(self):
        extra = ""
        if self.extra is not None:
            extra = self.extra[0]
        python = "/usr/bin/python2"
        if self.load:
            self.phase = "load"
            cmd = "{} /ycsb/bin/ycsb {} {} -s -P /tmp/ycsb/{} {}".format(
                python, self.phase, self.driver[0], self.workload, extra
            )
            stdout, stderr, rc = self._run(cmd)
            output = f"{stdout}\n{stderr}"
        else:
            self.phase = "run"
            cmd = "{} /ycsb/bin/ycsb {} {} -s -P /tmp/ycsb/{} {}".format(
                python, self.phase, self.driver[0], self.workload, extra
            )
            stdout, stderr, rc = self._run(cmd)
            output = f"{stdout}\n{stderr}"

        if rc != 0:
            print("YCSB failed to execute:\n%s", stderr)
            exit(1)
        if "Error inserting" in stderr:
            print("YCSB failed to load database... Drop previous YCSB database")
            exit(1)

        data = self._parse_stdout(output)
        print(output)
        documents, summary = self._json_payload(
            data,
            self.run[0],
            self.uuid,
            self.user,
            self.phase,
            self.workload,
            self.driver[0],
            self.recordcount,
            self.operationcount,
            self.cluster_name,
        )

        print("Attempting to index results...")
        if len(documents) > 0:
            for document in documents:
                yield document, "results"
        if len(summary) > 0:
            for document in summary:
                yield document, "summary"
