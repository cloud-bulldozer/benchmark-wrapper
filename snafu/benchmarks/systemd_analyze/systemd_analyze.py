#!/usr/bin/env python3
"""sample_benchmark hosts and export results."""
import datetime
import json
import logging
import os
import re
import subprocess

import distro

from snafu.benchmarks import Benchmark, BenchmarkResult

logger = logging.getLogger("snafu")


class systemd_analyze(Benchmark):  # pylint: disable=invalid-name
    """Wrapper for the systemd-analyze Test benchmark.
    cd /<working dir>/snafu
    ./run_snafu.py --tool systemd_analyze --create-archive
    """

    tool_name = "systemd_analyze"
    tc_values: list[str] = []
    td_values: list[str] = []

    # Test configuration lists
    tc_list = [
        "kversion",
        "cpumodel",
        "numcores",
        "maxMHz",
        "systemtgt",
    ]  # pylint: disable=attribute-defined-outside-init
    tc_values = []  # pylint: disable=attribute-defined-outside-init
    # Test data lists
    td_list = [
        "firmware",
        "loader",
        "kernel",
        "initrd",
        "userspace",
    ]  # pylint: disable=attribute-defined-outside-init
    td_values = []  # pylint: disable=attribute-defined-outside-init

    # Current date timestamp
    curtime = datetime.datetime.now().strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )  # pylint: disable=attribute-defined-outside-init
    short_curtime = datetime.datetime.now().strftime(
        "%Y-%m-%d"
    )  # pylint: disable=attribute-defined-outside-init

    def setup(self):  # pylint: disable=too-many-branches
        """
        No arguments at this time.
        args = (
            ConfigArgument(
               "--samples",
                help="Number of samples to perform.",
                dest="samples",
                env_var="SAMPLES",
                default=1,
                type=int,
            )
        )
        """
        self.config.parse_args()

        """Setup the systemd-analyze Test Benchmark."""  # pylint: disable=pointless-string-statement

        # Get test_config values
        #
        # kernel version
        # kversion_out = platform.release()
        kversion_out = subprocess.run(["uname", "-r"], stdout=subprocess.PIPE, check=False)
        kversion_out = kversion_out.stdout.decode("utf-8")
        self.tc_values.insert(0, kversion_out.strip())

        # cpu test config values
        cpuinfo_out = subprocess.run(["lscpu"], stdout=subprocess.PIPE, check=False)
        cpuinfo_out = cpuinfo_out.stdout.decode("utf-8")
        # cpu model
        model = None
        for line in cpuinfo_out.split("\n"):
            if "Model name:" in line:
                model = re.search("Model name.*:(.*)", cpuinfo_out).group(1)
        # Check for value
        if not model:
            self.tc_values.insert(1, "NULL")
        else:
            self.tc_values.insert(1, model.lstrip())

        # number of cores
        numcores = None
        for line in cpuinfo_out.split("\n"):
            if "CPU(s):" in line:
                numcores = re.search(r"CPU\(s\):(.*)", cpuinfo_out).group(1)
        # Check for value
        if not numcores:
            self.tc_values.insert(2, "NULL")
        else:
            self.tc_values.insert(2, numcores.strip())

        # CPU max MHz
        maxmhz = None
        for line in cpuinfo_out.split("\n"):
            if "CPU max MHz:" in line:
                maxmhz = re.search("CPU max MHz:(.*)", cpuinfo_out).group(1)
        # Check for value
        if not maxmhz:
            self.tc_values.insert(3, "NULL")
        else:
            self.tc_values.insert(3, maxmhz.strip())

        # systemctl target
        sysctl_out = subprocess.run(["systemctl", "get-default"], stdout=subprocess.PIPE, check=False)
        sysctl_out = sysctl_out.stdout.decode("utf-8")
        # Check for value
        if not sysctl_out:
            self.tc_values.insert(4, "NULL")
        else:
            self.tc_values.insert(4, sysctl_out.strip())

        self.sa_config = {}  # pylint: disable=attribute-defined-outside-init
        self.sa_config["test_config"] = {}
        for index in range(len(self.tc_list)):  # pylint: disable=consider-using-enumerate
            self.sa_config["test_config"][self.tc_list[index]] = self.tc_values[index]

        self.sa_config["test_config"]["distro"] = distro.info(True)
        distro_name = distro.name(pretty=True)
        distro_name = distro_name.replace(" ", "_")
        self.sa_config["test_config"]["distro"]["name"] = distro_name

        clustername = "unknown"
        if "clustername" in os.environ:
            clustername = os.environ["clustername"]
        self.sa_config["test_config"]["platform"] = clustername + "_" + distro_name + "_" + self.short_curtime
        return True

    def collect(self):
        """Run the systemd_analyze Test Benchmark and collect results."""

        ##########################
        # Exec systemd-analyze cmd
        sysd_out = subprocess.run(["systemd-analyze", "time"], stdout=subprocess.PIPE, check=False)
        sysd_out = sysd_out.stdout.decode("utf-8")

        # Parse cmd output and populate json dict
        for output_str in self.td_list:
            index = self.td_list.index(output_str)
            result = re.findall(r"(\d+\.\d+)s\s\(" + output_str + r"\)", sysd_out)
            if not result:
                self.td_values.insert(index, "")
            else:
                logger.debug("%s", result[0])
                self.td_values.insert(index, float(result[0]))

        ####################################
        # define json struct for data points
        data_point = {"date": self.curtime, "test_data": {}}

        for index in range(len(self.td_list)):  # pylint: disable=consider-using-enumerate
            data_point["test_data"][self.td_list[index]] = self.td_values[index]

        result: BenchmarkResult = self.create_new_result(
            data=data_point,
            config=self.sa_config,
            tag="summary",
        )

        logger.debug(json.dumps(result.to_jsonable(), indent=4))

        yield result

        blame_list = self.get_sa_blame()

        for blame_data_point in blame_list:
            result: BenchmarkResult = self.create_new_result(
                data=blame_data_point,
                config=self.sa_config,
                tag="blame",
            )

            logger.debug(json.dumps(result.to_jsonable(), indent=4))

            yield result

        #  blame_cmd = "systemd-analyze blame"
        #  critical-chain_cmd + "systemd-analyze critical-chain"

    def get_sa_blame(self):  # pylint: disable=missing-function-docstring

        blame_list = []

        # Exec systemd-analyze cmd
        sysd_out = subprocess.run(["systemd-analyze", "blame"], stdout=subprocess.PIPE, check=False)
        sysd_out = sysd_out.stdout.decode("utf-8")

        # Parse cmd output and populate json dict
        for line in sysd_out.split("\n"):

            words = re.split(r"\s", line)
            service = words[-1]
            minutes = re.search(r"(\d+)min", line)
            seconds = re.search(r"(\d+\.\d+)s", line)
            millisec = re.search(r"(\d+)ms", line)
            etime = None
            if minutes and seconds:
                min_var = minutes[0].strip("min")
                sec = seconds[0].strip("s")
                etime = str((int(min_var) * 60) + float(sec))
            elif seconds and not minutes:
                etime = seconds[0].strip("s")
            elif millisec:
                ms_var = millisec[0].strip("ms")
                etime = str((int(ms_var) / 1000) % 60)

            if service and etime:
                data_point = {"date": self.curtime, "test_data": {}}
                # print(f'{service}: {etime}')            # DEBUG
                data_point["test_data"]["name"] = service
                data_point["test_data"]["start_time"] = float(etime)

            blame_list.append(data_point)

        return blame_list

    def cleanup(self):
        """Cleanup the systemd-analyze Test Benchmark."""
        return True
