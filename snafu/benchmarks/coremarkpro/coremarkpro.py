# /usr/bin/env python3
"""Runs CoreMark Pro."""
import re
import shlex
import uuid
from collections.abc import Iterable
from datetime import datetime

from dateutil import tz

from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import ConfigArgument
from snafu.process import sample_process


class Coremarkpro(Benchmark):
    """Wrapper for CoreMark Pro"""

    # Set for Benchmark Class
    tool_name = "coremark-pro"
    args = (
        ConfigArgument(
            "-p",
            "--path",
            dest="path",
            type=str,
            help="Path to coremark-pro's directory",
            required=True,
        ),
        ConfigArgument(
            "-c",
            "--context",
            dest="context",
            type=int,
            help="CoreMark Pro's context",
            default=1,
            required=False,
        ),
        ConfigArgument(
            "-w",
            "--worker",
            help="CoreMark Pro's worker",
            dest="worker",
            type=int,
            default=0,
            required=False,
        ),
        ConfigArgument(
            "-s",
            "--sample",
            dest="sample",
            env_var="SAMPLE",
            default=1,
            type=int,
            help="Number of times to run the benchmark",
            required=False,
        ),
        ConfigArgument(
            "-r",
            "--result-name",
            dest="result_name",
            default="builds/linux64/gcc64/logs/linux64.gcc64",
            type=str,
            help="Name of CoreMark Pro's result files. Path is relative to `--path` and no extenstion.",
            required=False,
        ),
        ConfigArgument(
            "-i",
            "--ingest",
            dest="ingest",
            default=False,
            type=bool,
            help="Ingest results from previous CoreMark Run",
            required=False,
        ),
    )

    result_config: dict = {}

    """ Helper functions"""

    def build_workload_cmd(self) -> list[str]:
        """
        Builds the command line arguments needed to run CoreMark Pro
        """

        xcmd = f" -c{self.config.context} -w{self.config.worker}"
        return shlex.split(f"make TARGET=linux64 certify-all XCMD='{xcmd}'")

    def create_raw_results(self) -> Iterable[BenchmarkResult]:
        """
        Parses the raw results logs from CoreMark Pro into a Benchmark result. Ignores any median results.
        """

        headers = [
            "uid",
            "suite",
            "name",
            "ctx",
            "wrk",
            "fails",
            "t(s)",
            "iter",
            "iter/s",
            "codesize",
            "datasize",
        ]
        types = [str, str, str, int, int, int, float, int, float, int, int]

        with open(self.config.path + self.config.result_name + ".log", encoding="utf-8") as file:
            results: list[dict] = []
            prev_run_type = ""
            run_type = ""
            run_index = 0
            run_starttime = ""
            for line in file:
                # Look for the following string in the logs:
                #    Results for `run_type` started at `timestamp`
                result = re.search(r"^#Results for (\w+) .* (\d+:\d+:\d+:\d+) XCMD", line)
                if result:
                    prev_run_type = run_type
                    (run_type, run_starttime) = result.group(1, 2)
                    continue

                # Ignore median results since it can be derived
                if "median" not in line:
                    if re.search(r"^\d+", line):
                        # Adds a basic sequence number for the runs to avoid performance
                        # runs with the same result from being flagged as a duplicate.
                        if prev_run_type != run_type:
                            run_index = 0
                            prev_run_type = run_type
                        cols = re.split(r"\s+", line.rstrip())
                        converted_cols = [func(val) for func, val in zip(types, cols)]
                        record = dict(zip(headers, converted_cols))
                        record["type"] = run_type
                        record["starttime"] = self.convert_coremark_timestamp(run_starttime)
                        record["run_index"] = run_index
                        run_index += 1
                        results.append(record)
                        yield self.create_new_result(
                            data=record,
                            config=self.result_config,
                            tag="raw",
                        )

    def create_summary_results(self) -> Iterable[BenchmarkResult]:
        """
        Parses the CoreMark Pro's 'mark' file which has the scores calculated
        """

        headers = ["name", "multicore", "singlecore", "scaling"]
        types = [str, float, float, float]

        with open(self.config.path + self.config.result_name + ".mark", encoding="utf-8") as file:
            table_name = ""
            for line in file:
                line = line.rstrip()
                if not line:
                    continue

                # Find where the table starts and skips the fluff
                if "RESULTS TABLE" in line:
                    table_name = line.split(" ")[0].lower()
                    while True:
                        # Exit out of loop once it finds the table delimiter
                        # Disable pylint false positive, doesn't impact the generator
                        # pylint: disable=stop-iteration-return
                        if "---" in next(file):
                            break
                    continue

                cols = re.split(r"\s+", line.rstrip())
                converted_cols = [func(val) for func, val in zip(types, cols)]
                record = dict(zip(headers, converted_cols))
                record["type"] = table_name

                yield self.create_new_result(
                    data=record,
                    config=self.result_config,
                    tag="summary",
                )

    @staticmethod
    def convert_coremark_timestamp(timestamp) -> str:
        """
        Converts CoreMark Pro's timestamp in the raw logs into a ES friendly date format
        """

        time_obj = datetime.strptime(timestamp, "%y%j:%H:%M:%S")
        utc_tz = tz.gettz("UTC")

        return (time_obj.astimezone(utc_tz)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def setup(self) -> bool:

        # Parse the command line args
        self.config.parse_args()

        self.logger.info("Building CoreMark Pro")
        build = sample_process(
            ["make", "build"],
            self.logger,
            retries=2,
            expected_rc=0,
            cwd=self.config.path,
            env=self.config.get_env(),
        )
        result = next(iter(build))
        if not result.success:
            self.logger.critical(f"Failed to buiild CoreMark Pro! Got results: {result}")
            return False

        # Sets up defaults for the required variables
        if self.config.uuid is None:
            self.config.uuid = str(uuid.uuid4())
        if self.config.user is None:
            self.config.user = "myuser"
        if self.config.cluster_name is None:
            self.config.cluster_name = "mycluster"

        self.result_config["test_config"] = {
            "worker": self.config.worker,
            "context": self.config.context,
            "sample": self.config.sample,
        }

        return True

    def collect(self) -> Iterable[BenchmarkResult]:

        cmd = self.build_workload_cmd()

        if not self.config.ingest:
            samples = sample_process(
                cmd,
                self.logger,
                num_samples=self.config.sample,
                retries=2,
                expected_rc=0,
                cwd=self.config.path,
                env=self.config.get_env(),
            )

            for sample_num, sample in enumerate(samples):
                self.logger.info(f"Starting coremark-pro sample number {sample_num}")

                self.result_config["date"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                self.result_config["sample"] = sample_num
                if not sample.success:
                    self.logger.critical(f"Failed to run! Got results: {sample}")
                else:
                    yield from self.create_raw_results()
                    yield from self.create_summary_results()
        else:
            self.result_config["date"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            self.result_config["sample"] = self.config.sample
            yield from self.create_raw_results()
            yield from self.create_summary_results()

    def cleanup(self):
        return True
