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

import base64
import copy
import re
import subprocess
from datetime import datetime


class Trigger_pgbench:
    def __init__(self, args):
        self.port = args.port
        self.uuid = args.uuid
        self.user = args.user
        self.database = args.database
        self.description = args.description
        self.cluster_name = args.cluster_name
        self.run = args.run

        self.pgb_vers = args.pgb_vers
        self.run_start_timestamp = args.run_start_timestamp
        self.sample_start_timestamp = args.sample_start_timestamp
        self.index = "ripsaw-pgbench"

        # Initialize json payload shared metadata
        self.meta_processed = []
        self.meta_processed.append(
            {
                "workload": "pgbench",
                "pgb_vers": self.pgb_vers,
                "uuid": self.uuid,
                "user": self.user,
                "cluster_name": args.cluster_name,
                "iteration": int(args.run[0]),
                "database": self.database,
                "run_start_timestamp": self.run_start_timestamp,
                "sample_start_timestamp": self.sample_start_timestamp,
                "description": self.description,
            }
        )

    def _json_payload(self, meta_processed, data):
        processed = copy.deepcopy(meta_processed)
        for line in data["config"]:
            processed[0].update({f"{line[0]}": self._num_convert(line[1])})
        for line in data["results"]:
            processed[0].update({f"{line[0]}": self._num_convert(line[1])})
        return processed

    def _json_payload_raw(self, meta_processed, data):
        processed = copy.deepcopy(meta_processed)
        for line in data["config"]:
            processed[0].update({f"{line[0]}": self._num_convert(line[1])})
        processed[0].update({"raw_output_b64": data["raw_output_b64"].decode("utf-8")})
        return processed

    def _json_payload_prog(self, meta_processed, progress, data):
        processed = []
        for prog in progress:
            entry = copy.copy(meta_processed[0])
            for line in data["config"]:
                if "timestamp" not in line[0]:
                    entry.update({f"{line[0]}": self._num_convert(line[1])})
            entry.update(prog)
            processed.append(entry)
        return processed

    def _run_pgbench(self):
        cmd = "pgbench -P 10 --progress-timestamp $pgbench_opts"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), stderr.strip().decode("utf-8"), process.returncode

    def _num_convert(self, value):
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except:  # noqa
                pass
        except TypeError:
            pass
        return value

    def _parse_stdout(self, stdout):
        raw_output_b64 = base64.b64encode(stdout.encode("utf-8"))
        # pgbench outputs config values and results in either 'key:value'
        # or 'key=value' format. It's a bit inconsistent between versions
        # which information uses which format, and some of the output is
        # config info and some is benchmark results.
        #
        # We normalize everything to 'key:value' first, then extract from
        # the new list the outputs that are results and place them in a
        # new list.
        results = []
        config = stdout.splitlines()
        for idx, line in enumerate(config):
            config[idx] = line.replace(" = ", ":").split(":", 1)
            config[idx][0] = config[idx][0].replace(" ", "_").strip()
            config[idx][1] = self._num_convert(config[idx][1].strip())
            if re.search("tps|latency|processed", config[idx][0]):
                results.append(config[idx])
            if re.search("duration", config[idx][0]):
                config[idx][0] += "_seconds"
                config[idx][1] = self._num_convert(config[idx][1].split()[0])
        for idx, line in enumerate(results):
            if line in config:
                config.remove(line)
            if re.search("tps", results[idx][0]):
                cons = re.findall(r".*\((....)uding.*", results[idx][1])  # noqa
                if cons:
                    results[idx][0] = f"tps_{cons[0]}_con_est".strip()
                    results[idx][1] = self._num_convert(re.sub(r" \(.*", "", results[idx][1]).strip())  # noqa
            elif re.search("latency", results[idx][0]):
                results[idx][0] += "_ms"
                results[idx][1] = self._num_convert(results[idx][1].split(" ", 1)[0])
            elif re.search("processed", results[idx][0]):
                try:
                    results[idx][1] = self._num_convert(results[idx][1].split("/", 1)[0])
                except AttributeError:
                    pass
        config.append(["timestamp", datetime.now()])
        return {"config": config, "results": results, "raw_output_b64": raw_output_b64}

    def _parse_stderr(self, stderr):
        progress = []
        for line in stderr.splitlines():
            if "progress" in line:
                progress.append(
                    {
                        "timestamp": datetime.fromtimestamp(float(line.split(" ")[1])),
                        "tps": float(line.split(" ")[3]),
                        "latency_ms": float(line.split(" ")[6]),
                        "stddev": float(line.split(" ")[9]),
                    }
                )
        return progress

    def _summarize_data(self, data, iteration, uuid, database, pgb_vers):
        print("+{} PGBench Results {}+".format("-" * (50), "-" * (50)))
        print(f"PGBench version: {pgb_vers}")
        print("")
        print(f"UUID: {uuid}")
        print(f"Run: {iteration}")
        print("")
        print(f"Database: {database}")
        print("")
        print("PGBench run info:")
        for line in data["config"]:
            print(f"          {line[0]}: {line[1]}")
        print("")
        # I asked for a mai tai, and they brought me a pina colada,
        # and I said no salt, NO salt on the margarita, but it had salt
        # on it, big grains of salt, floating in the glass.
        print("TPS report:")
        for line in data["results"]:
            print(f"          {line[0]}: {line[1]}")
        print("")
        print("+{}+".format("-" * (115)))

    def emit_actions(self):
        output = self._run_pgbench()
        if output[2] == 1:
            print("PGBench failed to execute, trying one more time..")
            output = self._run_pgbench()
            if output[2] == 1:
                print("PGBench failed to execute a second time, stopping...")
                exit(1)
        data = self._parse_stdout(output[0])
        progress = self._parse_stderr(output[1])
        documents = self._json_payload(self.meta_processed, data)
        documents_raw = self._json_payload_raw(self.meta_processed, data)
        documents_prog = self._json_payload_prog(self.meta_processed, progress, data)
        print(output[0])
        if len(documents) > 0:
            self._summarize_data(data, self.run[0], self.uuid, self.database, self.pgb_vers)
        print("\n")
        print(documents)
        print("\n")
        if len(documents) > 0:
            for document in documents:
                yield document, "summary"

        if len(documents_raw) > 0:
            for document in documents_raw:
                yield document, "raw"

        if len(documents_prog) > 0:
            for document in documents_prog:
                yield document, "results"
