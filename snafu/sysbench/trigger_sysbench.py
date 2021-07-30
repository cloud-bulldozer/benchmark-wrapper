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

import subprocess
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger("snafu")


class trigger_sysbench:
    def __init__(self, uuid, user, cluster_name, sysbench_file, sample):

        self.uuid = uuid
        self.user = user
        self.cluster_name = cluster_name
        self.sysbench_file = sysbench_file
        self.sample = sample

        #  blank dictionary to capture test configuration
        self.test_config = {}

    def _run_sysbench(self):

        """
        loop through each option in config file and add it to the command line option,
        and test_confg then run the command. this we reduce our dependency on
        specific sysbench versions/future changes.
        """

        #  open config file
        config_file = open(self.sysbench_file, "r")

        cmd = "/usr/bin/sysbench"
        #  for each option add it to the command line
        for option in config_file:
            option = option.strip()
            #  need to use --test for ease of use when parsing, but will strip off before adding to cmd
            if "--test" in option:
                cmd = cmd + " " + option.replace("--test=", "")
            else:
                cmd = cmd + " " + option
            #  slipt option Key=Value pair up and remove --
            o, v = option.split("=")
            #  insert Key value pair into test config
            self.test_config[o.replace("--", "")] = v
        #  add run as the last option to the command line
        cmd = cmd + " run"

        #  log the entire command
        logger.info("Executing %s" % cmd)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, cwd=os.getcwd())
        #  run command and capture standard out and error
        stdout, stderr = process.communicate()

        if stderr is not None:
            stderr = stderr.decode("utf-8")

        return stdout.strip().decode("utf-8"), stderr, process.returncode

    def emit_actions(self):

        sample_starttime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        # run the sysbench test
        stdout, stderr, rc = self._run_sysbench()
        #  setup result summary dictionary
        sysbench_result_summary = {
            "uuid": self.uuid,
            "user": self.user,
            "clustername": self.cluster_name,
            "date": sample_starttime,
            "sample": self.sample,
            "test_config": self.test_config,
        }
        #  this needs to be filled out when parsing stdout results

        #  if the return code is not 0 then log a failure, else log a successful run
        if rc != 0:
            logger.error("failed to parse the output file")
            logger.error(stdout, stderr)
            exit(1)

        logger.info("sysbench has successfully finished \n")
        #  remove spacing for better parsing
        nospace_stdout = stdout.replace(" ", "")
        section = None
        test_results = {}
        # loop through each line in stdout and capture results
        for line in nospace_stdout.splitlines():
            #  all result fields have : so targeting those lines

            if "transferred" in line and "memory" in self.test_config["test"]:
                mem_total_transfered, mem_total_transferedpersecond = line.split("transferred")
                mem_total_transfered = float(mem_total_transfered.replace("MiB", ""))

                mem_total_transferedpersecond = re.sub("[()]", "", mem_total_transferedpersecond)
                mem_total_transferedpersecond = float(mem_total_transferedpersecond.replace("MiB/sec", ""))

                test_results["transferred(MiB)"] = mem_total_transfered
                test_results["transferredpersec(MiB/sec)"] = mem_total_transferedpersecond
            if ":" in line:
                #  break the line into Key value pairs
                key, value = line.split(":")
                #  the only time there is a : and no value is when there is a section
                #  if there is no section just place at top of structure
                #  if section has been found place K:V pairs under it
                if value == "":
                    #  each test has a long string for options, so we are reducing that just to options
                    #  this section is not standard and we loss options so list them all in test_config
                    if "options" in key:
                        section = "options"
                    else:
                        section = key
                    #  create a nested dict
                    test_results[section] = {}
                elif section is None:
                    test_results[key] = float(value)
                else:
                    #  there are fields with two values, we need to identify them and break
                    #  them down into two sub-fields
                    if "(avg/stddev)" in key:
                        key = key.replace("(avg/stddev)", "")
                        avg, stddev = value.split("/")
                        test_results[section][key] = {}
                        test_results[section][key]["avg"] = float(avg)
                        test_results[section][key]["stddev"] = float(stddev)
                    elif "Totaloperations" in key and "persecond" in value:
                        totaloperations, totaloperationspersecond = value.split("(")
                        totaloperationspersecond = totaloperationspersecond.replace("persecond)", "")
                        test_results[section]["Totaloperations"] = float(totaloperations)
                        test_results[section]["Totaloperationspersecond"] = float(totaloperationspersecond)
                    elif "totaltime" in key:
                        key = key + "(seconds)"
                        value = value.replace("s", "")
                        test_results[section][key] = float(value)
                    elif "option" not in section:
                        test_results[section][key] = float(value)
                    else:
                        #  store the Key value pair in the appropriate section
                        test_results[section][key] = value

        #  logger.info(json.dumps(test_results, indent=4))
        logger.info(stdout)

        sysbench_result_summary["test_results"] = test_results
        yield sysbench_result_summary, "summary"
