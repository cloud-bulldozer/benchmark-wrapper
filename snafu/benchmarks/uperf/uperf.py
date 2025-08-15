#!/usr/bin/env python3
"""Wrapper for running the uperf benchmark. See http://uperf.org/ for more information."""
import dataclasses
import datetime
import re
import shlex
import sys
from collections.abc import Iterable
from typing import Any

import numpy as np

from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import Config, ConfigArgument, FuncAction, check_file, none_or_type
from snafu.process import sample_process


class ParseRangeAction(FuncAction):
    """Parses node_range and density_range attributes."""

    @staticmethod
    def func(arg: str) -> list[int]:
        """Take the input argument, split by '-' and cast non-empty results into ints."""
        return [int(x) for x in arg.split("-") if x != ""]


@dataclasses.dataclass
class RawUperfStat:
    """Represents a raw Uperf statistic outputted through stdout."""

    timestamp: float
    bytes: int
    ops: int


@dataclasses.dataclass
class UperfStdout:
    """
    Represents stdout from a Uperf benchmark run.

    Note that some attributes are included which may not appear in all stdout of Uperf. Within the
    cloud-bulldozer organization, we use benchmark-wrapper with specific profile names that have
    the following format: ``test-proto-wsize-rsize-nthr``. Uperf prints the profile name to stdout, which
    we parse within the benchmark wrapper and store in this class.
    """

    results: tuple[RawUperfStat, ...]
    duration: int
    test_type: str | None = None
    protocol: str | None = None
    message_size: int | None = None
    read_message_size: int | None = None
    num_threads: int | None = None


@dataclasses.dataclass
class UperfConfig:
    """Container for common configuration options that are passed to Uperf."""

    test_type: str | None = None
    protocol: str | None = None
    message_size: int | None = None
    read_message_size: int | None = None
    num_threads: int | None = None
    duration: int | None = None
    kind: str | None = None
    hostnetwork: str | None = None
    remote_ip: str | None = None
    client_ips: str | None = None
    service_ip: str | None = None
    service_type: str | None = None
    port: str | None = None
    client_node: str | None = None
    server_node: str | None = None
    num_pairs: str | None = None
    multus_client: str | None = None
    networkpolicy: str | None = None
    density: str | None = None
    nodes_in_iter: str | None = None
    step_size: str | None = None
    colocate: str | None = None
    density_range: list[int] | None = None
    node_range: list[int] | None = None
    pod_id: str | None = None

    @classmethod
    def new(cls, stdout: UperfStdout, config: Config):
        """Create a new instance given instances of :py:mod:`~snafu.config.Config` and UperfStdout."""

        kwargs: dict[str, Any] = {}
        for fields in dataclasses.fields(cls):
            val = getattr(stdout, fields.name, None)
            if val is None:
                val = getattr(config, fields.name, None)
            kwargs[fields.name] = val
        return cls(**kwargs)


@dataclasses.dataclass
class UperfStat:
    """Parsed Uperf Statistic."""

    uperf_ts: str
    timestamp: str
    bytes: int
    norm_byte: int
    ops: int
    norm_ops: int
    norm_ltcy: float
    iteration: int | None = None


class Uperf(Benchmark):
    """Wrapper for the uperf benchmark."""

    tool_name = "uperf"
    args = (
        ConfigArgument(
            "-w",
            "--workload",
            dest="workload",
            env_var="WORKLOAD",
            help="Provide XML workload location",
            required=True,
        ),
        ConfigArgument(
            "-s",
            "--sample",
            dest="sample",
            env_var="SAMPLE",
            default=1,
            type=int,
            help="Number of times to run the benchmark",
            required=True,
        ),
        ConfigArgument(
            "--resourcetype",
            dest="kind",
            env_var="RESOURCETYPE",
            help="Provide the resource type for uperf run - pod/vm/baremetal",
            required=True,
        ),
        # These need help text
        ConfigArgument("--ips", dest="client_ips", env_var="ips", default=""),
        ConfigArgument("--remoteip", dest="remote_ip", env_var="h", default=""),
        ConfigArgument("--hostnet", dest="hostnetwork", env_var="hostnet", default="False"),
        ConfigArgument("--serviceip", dest="service_ip", env_var="serviceip", default="False"),
        ConfigArgument("--servicetype", dest="service_type", env_var="servicetype", default=""),
        ConfigArgument("--port", dest="port", env_var="port", default="30000"),
        ConfigArgument("--server-node", dest="server_node", env_var="server_node", default=""),
        ConfigArgument("--client-node", dest="client_node", env_var="client_node", default=""),
        ConfigArgument("--num-pairs", dest="num_pairs", env_var="num_pairs", default=""),
        ConfigArgument("--multus-client", dest="multus_client", env_var="multus_client", default=""),
        ConfigArgument(
            "--network-policy",
            dest="networkpolicy",
            env_var="networkpolicy",
            default="",
        ),
        ConfigArgument("--nodes-count", dest="nodes_in_iter", env_var="node_count", default=""),
        ConfigArgument("--pod-density", dest="density", env_var="pod_count", default=""),
        ConfigArgument("--colocate", dest="colocate", env_var="colocate", default=""),
        ConfigArgument("--step-size", dest="step_size", env_var="stepsize", default=""),
        ConfigArgument("--test-type", dest="test_type", env_var="test_type", default=""),
        ConfigArgument("--proto", dest="protocol", env_var="proto", default=""),
        ConfigArgument(
            "--rsize",
            dest="read_message_size",
            env_var="rsize",
            default=None,
            type=none_or_type(int),
        ),
        ConfigArgument(
            "--wsize",
            dest="message_size",
            env_var="wsize",
            default=None,
            type=none_or_type(int),
        ),
        ConfigArgument("--nthr", dest="num_threads", env_var="nthr", default=1, type=int),
        # density_range and node_range are defined and exported in the cr file
        # it will appear in ES as startvalue-endvalue, for example
        # 5-10, for a run that began with 5 nodes involved and ended with 10
        ConfigArgument(
            "--density-range",
            dest="density_range",
            env_var="density_range",
            default="",
            action=ParseRangeAction,
        ),
        ConfigArgument(
            "--node-range",
            dest="node_range",
            env_var="node_range",
            default="",
            action=ParseRangeAction,
        ),
        # each node will run with density number of pods, this is the 0 based
        # number of that pod, useful for displaying throughput of each density
        ConfigArgument("--pod-id", dest="pod-id", env_var="my_pod_idx", default=""),
    )

    def parse_stdout(self, stdout: str) -> UperfStdout:
        """
        Return parsed stdout of Uperf sample.

        Parameters
        ----------
        stdout : str
            Raw stdout from Uperf to parse
        Returns
        -------
        UperfStdout
        """

        # This will effectivly give us:
        # <profile name="{{test}}-{{proto}}-{{wsize}}-{{rsize}}-{{nthr}}">
        profile_name = re.findall(r"running profile:(.*) \.\.\.", stdout)[0]
        vals = profile_name.split("-")
        parsed_profile_name_types: dict[str, type] = {
            "test_type": str,
            "protocol": str,
            "message_size": int,
            "read_message_size": int,
            "num_threads": int,
        }
        parsed_profile_name: dict[str, str | int | None] = {}
        if len(vals) != 5:
            self.logger.warning(
                f"Unable to parse detected profile name: {profile_name}. Expected format of "
                "'test_name-protocol-message_size-read_message_size-num_threads'"
            )
            parsed_profile_name = {key: None for key in parsed_profile_name_types}
        else:
            overwritten: list[str] = []
            for i, (key, cast) in enumerate(parsed_profile_name_types.items()):
                if getattr(self.config, key, None) is not None:
                    overwritten.append(key)
                parsed_profile_name[key] = cast(vals[i])
            if len(overwritten) > 0:
                self.logger.warning(
                    "The following params will be overwritten due to values found in workload "
                    f"profile name: {', '.join(overwritten)}"
                )

        # This will yeild us this structure :
        #     timestamp, number of bytes, number of operations
        # [('1559581000962.0330', '0', '0'), ('1559581001962.8459', '4697358336', '286704') ]
        tx_str = "Txn1" if parsed_profile_name["test_type"] == "connect" else "Txn2"
        results = re.findall(rf"timestamp_ms:(.*) name:{tx_str} nr_bytes:(.*) nr_ops:(.*)", stdout)
        # We assume message_size=write_message_size to prevent breaking dependant implementations

        uperf_stdout = UperfStdout(
            results=tuple(
                RawUperfStat(timestamp=float(r[0]), bytes=int(r[1]), ops=int(r[2])) for r in results
            ),
            duration=len(results),
        )

        for key, value in parsed_profile_name.items():
            setattr(uperf_stdout, key, value)
        return uperf_stdout

    @staticmethod
    def get_results_from_stdout(stdout: UperfStdout) -> list[UperfStat]:
        """
        Return list of results given raw uperf stdout.

        Uperf will output its statistics on newlines as it runs. The goal of this method is to
        return each of those statictics within a :py:class:`UperfStat` instance.
        Parameters
        ----------
        stdout : UperfStdout
            Parsed stdout from Uperf run.
        Returns
        -------
        list of UperfStat
        """

        processed: list[UperfStat] = []
        prev_bytes: int = 0
        prev_ops: int = 0
        prev_timestamp: float = 0.0
        num_bytes: int = 0
        ops: int = 0
        timestamp: float = 0.0
        norm_ops: int = 0
        norm_ltcy: float = 0.0

        for result in stdout.results:
            timestamp, num_bytes, ops = result.timestamp, result.bytes, result.ops

            norm_ops = ops - prev_ops
            if norm_ops != 0 and prev_timestamp != 0.0:
                norm_ltcy = ((timestamp - prev_timestamp) / norm_ops) * 1000

                datapoint = UperfStat(
                    uperf_ts=datetime.datetime.fromtimestamp(int(timestamp) / 1000).isoformat(),
                    timestamp=datetime.datetime.fromtimestamp(int(timestamp) / 1000).isoformat(),
                    bytes=num_bytes,
                    norm_byte=num_bytes - prev_bytes,
                    ops=ops,
                    norm_ops=norm_ops,
                    norm_ltcy=norm_ltcy,
                )

                processed.append(datapoint)
            prev_timestamp, prev_bytes, prev_ops = timestamp, num_bytes, ops

        return processed

    def setup(self) -> bool:
        """Parse config and check that workload file exists."""
        self.config.parse_args()
        self.logger.debug(f"Got config: {vars(self.config)}")

        if not getattr(self.config, "user", False) or not getattr(self.config, "uuid", False):
            self.logger.critical("Missing required metadata. Need both user and uuid to continue")
            return False

        if not check_file(self.config.workload):
            self.logger.critical(f"Unable to read workload file located at {self.config.workload}")
            return False

        return True

    def collect(self) -> Iterable[BenchmarkResult]:
        """
        Run uperf benchmark ``self.config.sample`` number of times.

        Returns immediately if a sample fails. Will attempt to Uperf run three times for each sample.
        """

        cmd = shlex.split(f"uperf -v -a -R -i 1 -m {self.config.workload} -P {self.config.port}")
        _plural = "s" if self.config.sample > 1 else ""
        self.logger.info(f"Collecting {self.config.sample} sample{_plural} of Uperf")

        samples = sample_process(
            cmd,
            self.logger,
            num_samples=self.config.sample,
            retries=2,
            expected_rc=0,
            env=self.config.get_env(),
        )

        for sample_num, sample in enumerate(samples):
            if not sample.success:
                self.logger.critical(f"Uperf failed to run! Got results: {sample}")
                sys.exit(1)

            self.logger.info(f"Finished collecting sample {sample_num}")
            self.logger.debug(f"Got sample: {sample}")

            if sample.successful.stdout is None:
                self.logger.critical(f"Uperf ran successfully, but didn't get stdout. Got results: {sample}")
                sys.exit(1)

            # Only show the full output if debug is enabled
            self.logger.debug(sample.successful.stdout)

            stdout: UperfStdout = self.parse_stdout(sample.successful.stdout)
            result_data: list[UperfStat] = self.get_results_from_stdout(stdout)
            config: UperfConfig = UperfConfig.new(stdout, self.config)

            byte_summary = []
            lat_summary = []
            op_summary = []
            for result_datapoint in result_data:
                byte_summary.append(result_datapoint.norm_byte)
                lat_summary.append(result_datapoint.norm_ltcy)
                op_summary.append(result_datapoint.norm_ops)
                result_datapoint.iteration = sample_num
                result: BenchmarkResult = self.create_new_result(
                    data=dataclasses.asdict(result_datapoint),
                    config=dataclasses.asdict(config),
                    tag="results",
                )
                self.logger.debug(f"Got sample result: {result}")
                yield result
            self.logger.info(f"{'-' * 50}")
            self.logger.info(f"Summary result for sample : {sample_num}")
            self.logger.info(f"Average byte : {np.average(byte_summary)}")
            self.logger.info(f"Average ops : {np.average(op_summary)}")
            self.logger.info(f"95%ile Latency(ms) : {np.percentile(lat_summary, 95)}")
            self.logger.info(f"{'-' * 50}")
        self.logger.info(f"Successfully collected {self.config.sample} sample{_plural} of Uperf.")

    @staticmethod
    # pylint: disable-next=arguments-differ
    def cleanup() -> bool:
        """Uperf doesn't have any cleanup tasks, therefore this method just returns ``True``."""
        return True
