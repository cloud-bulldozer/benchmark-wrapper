#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the uperf benchmark. See http://uperf.org/ for more information."""
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re
import datetime
import dataclasses
import shlex
from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import Config, ConfigArgument, FuncAction, check_file
from snafu.process import sample_process, ProcessSample


class ParseRangeAction(FuncAction):
    """Parses node_range and density_range attributes."""

    def func(self, arg: str) -> List[int]:
        return [int(x) for x in arg.split("-") if x != ""]


@dataclasses.dataclass
class RawUperfStat:
    timestamp: float
    bytes: int
    ops: int


@dataclasses.dataclass
class UperfStdout:
    results: Tuple[RawUperfStat, ...]
    test_type: str
    protocol: str
    message_size: int
    read_message_size: int
    num_threads: int
    duration: int


@dataclasses.dataclass
class UperfConfig:
    # Parsed from stdout
    test_type: str
    protocol: str
    message_size: int
    read_message_size: int
    num_threads: int
    duration: int
    # Given through args
    kind: str
    hostnetwork: Optional[str] = None
    remote_ip: Optional[str] = None
    client_ips: Optional[str] = None
    service_ip: Optional[str] = None
    client_node: Optional[str] = None
    server_node: Optional[str] = None
    num_pairs: Optional[str] = None
    multus_client: Optional[str] = None
    networkpolicy: Optional[str] = None
    density: Optional[str] = None
    nodes_in_iter: Optional[str] = None
    step_size: Optional[str] = None
    colocate: Optional[str] = None
    density_range: Optional[List[int]] = None
    node_range: Optional[List[int]] = None
    pod_id: Optional[str] = None

    @classmethod
    def new(cls, stdout: UperfStdout, config: Config):
        kwargs: Dict[str, Any] = dict()
        for fields in dataclasses.fields(cls):
            kwargs[fields.name] = getattr(stdout, fields.name, getattr(config, fields.name, None))
        return cls(**kwargs)


@dataclasses.dataclass
class UperfStat:
    uperf_ts: datetime.datetime
    bytes: int
    norm_byte: int
    ops: int
    norm_ops: int
    norm_ltcy: float
    iteration: Optional[int] = None


class Uperf(Benchmark):
    """
    Wrapper for the uperf benchmark.
    """

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
        ConfigArgument("-h", "--remoteip", dest="remote_ip", env_var="h", default=""),
        ConfigArgument("--hostnet", dest="hostnetwork", env_var="hostnet", default="False"),
        ConfigArgument("--serviceip", dest="service_ip", env_var="serviceip", default="False"),
        ConfigArgument("--server-node", dest="server_node", env_var="server_node", default=""),
        ConfigArgument("--client-node", dest="client_node", env_var="client_node", default=""),
        ConfigArgument("--num-pairs", dest="num_pairs", env_var="num_pairs", default=""),
        ConfigArgument("--multus-client", dest="multus_client", env_var="multus_client", default=""),
        ConfigArgument("--network-policy", dest="networkpolicy", env_var="networkpolicy", default="",),
        ConfigArgument("--nodes-count", dest="nodes_in_iter", env_var="node_count", default=""),
        ConfigArgument("--pod-density", dest="density", env_var="pod_count", default=""),
        ConfigArgument("--colocate", dest="colocate", env_var="colocate", default=""),
        ConfigArgument("--step-size", dest="step_size", env_var="stepsize", default=""),
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
            "--node-range", dest="node_range", env_var="node_range", default="", action=ParseRangeAction,
        ),
        # each node will run with density number of pods, this is the 0 based
        # number of that pod, useful for displaying throughput of each density
        ConfigArgument("--pod-id", dest="pod-id", env_var="my_pod_idx", default=""),
        # metadata
        ConfigArgument("--cluster-name", dest="cluster_name", env_var="clustername", default=""),
        ConfigArgument(
            "-u", "--uuid", dest="uuid", env_var="UUID", help="Provide UUID of run", required=True,
        ),
        ConfigArgument("--user", dest="user", env_var="USER", help="Provide user", required=True),
    )

    @staticmethod
    def parse_stdout(stdout: str) -> UperfStdout:
        """Return parsed stdout of Uperf sample."""

        # This will effectivly give us:
        # <profile name="{{test}}-{{proto}}-{{wsize}}-{{rsize}}-{{nthr}}">
        config = re.findall(r"running profile:(.*) \.\.\.", stdout)[0]
        test_type, protocol, wsize, rsize, nthr = config.split("-")
        # This will yeild us this structure :
        #     timestamp, number of bytes, number of operations
        # [('1559581000962.0330', '0', '0'), ('1559581001962.8459', '4697358336', '286704') ]
        results = re.findall(r"timestamp_ms:(.*) name:Txn2 nr_bytes:(.*) nr_ops:(.*)", stdout)
        # We assume message_size=write_message_size to prevent breaking dependant implementations

        return UperfStdout(
            results=tuple(
                RawUperfStat(timestamp=float(r[0]), bytes=int(r[1]), ops=int(r[2])) for r in results
            ),
            test_type=test_type,
            protocol=protocol,
            message_size=int(wsize),
            read_message_size=int(rsize),
            num_threads=int(nthr),
            duration=len(results),
        )

    def get_results_from_stdout(self, stdout: UperfStdout) -> List[UperfStat]:
        """Return list of results given raw uperf stdout."""

        processed: List[UperfStat] = []
        prev_bytes: int = 0
        prev_ops: int = 0
        prev_timestamp: float = 0.0
        bytes: int = 0
        ops: int = 0
        timestamp: float = 0.0
        norm_ops: int = 0
        norm_ltcy: float = 0.0

        for result in stdout.results:
            timestamp, bytes, ops = result.timestamp, result.bytes, result.ops

            norm_ops = ops - prev_ops
            if norm_ops == 0:
                norm_ltcy = 0.0
            else:
                norm_ltcy = ((timestamp - prev_timestamp) / norm_ops) * 1000

            datapoint = UperfStat(
                uperf_ts=datetime.datetime.fromtimestamp(int(timestamp) / 1000),
                bytes=bytes,
                norm_byte=bytes - prev_bytes,
                ops=ops,
                norm_ops=norm_ops,
                norm_ltcy=norm_ltcy,
            )

            processed.append(datapoint)
            prev_timestamp, prev_bytes, prev_ops = timestamp, bytes, ops

        return processed

    def setup(self) -> bool:
        """Parse config and check that workload file exists."""
        self.config.parse_args()
        self.logger.debug(f"Got config: {vars(self.config)}")

        if not check_file(self.config.workload):
            self.logger.critical(f"Unable to read workload file located at {self.config.workload}")
            return False

        return True

    def run(self) -> Iterable[BenchmarkResult]:
        """
        Run uperf benchmark ``self.config.sample`` number of times.

        Returns immediately if a sample fails. Will attempt to Uperf run three times for each sample.
        """

        self.logger.info("Running setup tasks.")
        if not self.setup():
            self.logger.critical(f"Something went wrong during setup, refusing to run.")
            return

        cmd = shlex.split(f"uperf -v -a -R -i 1 -m {self.config.workload}")

        for sample_num in range(1, self.config.sample + 1):
            self.logger.info(f"Starting Uperf sample number {sample_num}")
            sample: ProcessSample = sample_process(
                cmd,
                self.logger,
                retries=2,
                expected_rc=0,
                env={
                    env_var: getattr(self.config, dest) for env_var, dest in self.config.env_to_params.items()
                },
            )

            if not sample.success:
                self.logger.critical(f"Uperf failed to run! Got results: {sample}")
                return
            else:
                self.logger.info(f"Finished collecting sample {sample_num}")
                self.logger.debug(f"Got sample: {sample}")

                if sample.successful.stdout is None:
                    self.logger.critical(
                        f"Uperf ran successfully, but didn't get stdout. Got results: {sample}"
                    )
                    return

                stdout: UperfStdout = self.parse_stdout(sample.successful.stdout)
                result_data: List[UperfStat] = self.get_results_from_stdout(stdout)
                config: UperfConfig = UperfConfig.new(stdout, self.config)

                for result_datapoint in result_data:
                    result_datapoint.iteration = sample_num
                    result: BenchmarkResult = self.create_new_result(
                        data=dataclasses.asdict(result_datapoint),
                        config=dataclasses.asdict(config),
                        label="results",
                    )
                    self.logger.debug(f"Got sample result: {result}")
                    yield result

        self.logger.info(f"Successfully collected {self.config.sample} samples of Uperf.")
