#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the dnsperf benchmark.
See https://dns-oarc.net/tools/dnsperf for more information."""
import random
from datetime import datetime
from typing import Optional, Tuple, Union
from pathlib import Path
import dataclasses

import dateutil.parser
from pydantic import BaseModel
import pydantic.dataclasses
from ttp import ttp
import toolz

from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import Config, ConfigArgument
from snafu.process import ProcessSample, sample_process


class DnsRttSample(BaseModel):
    fqdn: str
    rtt_s: float
    qtype: str
    response_state: str


class ThroughputSample(BaseModel):
    timestamp: datetime
    throughput: float


DnsperfSample = Union[DnsRttSample, ThroughputSample]


@pydantic.dataclasses.dataclass
class DnsperfStdout:
    throughput_ts: Tuple[ThroughputSample, ...]
    rtt_samples: Tuple[DnsRttSample, ...]
    sum_rtt: float
    queries_sent: int
    queries_completed: int
    throughput_mean: float
    start_time: datetime
    dnsperf_version: str
    time_window_size: float
    load_mean: Optional[float] = None

    def __post_init_post_parse__(self):
        self.load_mean = self.queries_sent / self.time_window_size
<<<<<<< HEAD
=======
        print(self.load_mean)
>>>>>>> 1c03b18 (refactor mean_load to load_mean to follow load_limit convention)


class DnsperfConfig(BaseModel):
    address: str
    port: int
    query_filepath: str
    start_time: datetime
    sum_rtt: float
    dnsperf_version: str
    clients: int
    time_window_size: float
    transport_mode: str
    timeout_len: float
    # the load limit number is parsed to a string,
    # so that it can be stored as a discrete
    # variable; one possible value is infinity
    load_limit: Optional[float] = float("inf")
    networkpolicy: Optional[str] = None
    network_type: Optional[str] = None
    pod_id: Optional[str] = None
    node_id: Optional[str] = None

    @classmethod
    def new(cls, stdout: DnsperfStdout, config: Config, load):
        """
        Merge attributes parsed from stdout and config.
        """
        # merge dictionaries (right-most dictionary takes precedence)
        # then, unpack merged dictionary
        return cls(**toolz.merge(config.params.__dict__, dataclasses.asdict(stdout)), load_limit=load)


class Dnsperf(Benchmark):
    """
    Wrapper for the dnsperf benchmark.
    """

    tool_name = "dnsperf"
    with Path(__file__).with_name("dnsperf-template.xml").open() as template_f:
        output_template = template_f.read()

    args = (
        ConfigArgument(
            "-q",
            "--queries",
            dest="query_filepath",
            env_var="queries",
            required=True,
            help="filepath to a list of DNS queries",
        ),
        ConfigArgument("-l", "--load-sequence", dest="load_sequence", type=int, nargs="+", default=list()),
        ConfigArgument(
            "-a",
            "--address",
            dest="address",
            help="IPv4 address of DNS server to test",
            default="172.30.0.10",
        ),
        ConfigArgument("-p", "--port", dest="port", help="Port on which DNS packets are sent.", default="53"),
        ConfigArgument(
            "-c",
            "--clients",
            dest="clients",
            help="Quantity of clients to act as. (1 client : 1 thread)",
            default="1",
        ),
        ConfigArgument(
            "-w",
            "--time-window-size",
            dest="time_window_size",
            env_var="time_window_size",
            help="Time window size for test",
            default=".01",
        ),
        ConfigArgument("--timeout", help="Length of timeout in seconds", dest="timeout_len", default="5"),
        ConfigArgument(
            "-m",
            "--transport-mode",
            dest="transport_mode",
            help="set transport mode: udp, tcp, dot",
            default="udp",
        ),
        ConfigArgument(
            "-S",
            "--throughput-time-interval",
            dest="throughput_time_interval",
            help="time interval at which to check dns throughput",
            default=".0011",  # smallest interval
        ),
        ConfigArgument("--network-policy", dest="networkpolicy", env_var="networkpolicy"),
        ConfigArgument("--network-type", dest="network_type", env_var="network_type"),
        ConfigArgument("--pod-id", dest="pod_id", default=None),
        ConfigArgument("--node-id", dest="node_id", default=None),
        ConfigArgument("--rng-seed", dest="rng_seed", default=1),
    )

    def setup(self) -> bool:
        """Setup dnsperf benchmark."""
        self.logger.info("Setting up dnsperf benchmark.")
        self.config.parse_args()
        self.config.load_sequence.append(float("inf"))
        # dynamically set timeout length for template parser
        self.output_template = (
            self.output_template + "\n"
            "<vars>"
            "default_values = {"
            f"'rtt_s': {self.config.timeout_len}"
            "}"
            "</vars>\n"
        )
        return True

    def cleanup(self) -> bool:
        """Clean up artifacts from the dnsperf benchmark."""
        self.logger.info("Cleaning up dnsperf benchmark.")
        return True

    def collect(self) -> BenchmarkResult:
        """Run the dnsperf benchmark and collect results."""

        self.logger.info("Starting dnsperf")
        for load_limit in self.config.load_sequence:
            cmd = [
                "dnsperf",
                "-v",  # print latency information for each query
                "-s",
                self.config.address,
                "-p",
                self.config.port,
                "-d",
                self.config.query_filepath,
                "-T",
                self.config.clients,
                "-l",
                self.config.time_window_size,
                "-t",
                self.config.timeout_len,
                "-m",
                self.config.transport_mode,
                "-S",
                self.config.throughput_time_interval,
            ]

            if isinstance(load_limit, int):
                cmd = [*cmd, "-Q", str(load_limit)]

            sample: ProcessSample = sample_process(
                cmd, self.logger,
            )

            if not sample.success:
                self.logger.critical(f"dnsperf failed to complete! Got results: {sample}\n")
                return None
            elif sample.successful.stdout is None:
                self.logger.critical(
                    (
                        "dnsperf ran successfully, but did not get output on stdout.\n"
                        f"Got results: {sample}\n"
                    )
                )
                return None

            stdout: DnsperfStdout = self.parse_process_output(sample.successful.stdout)
            cfg: DnsperfConfig = DnsperfConfig.new(stdout, self.config, load=load_limit)
            # change load limit to string for Elasticsearch
            cfg.load_limit = str(load_limit)

            # prepare stdout data for JSON serialization
            cfg.load_limit = str(load_limit)
            stdout.throughput_ts = [item.dict() for item in stdout.throughput_ts]
            stdout.rtt_samples = [item.dict() for item in stdout.rtt_samples]

            yield self.create_new_result(
                data=dataclasses.asdict(stdout), config=dict(cfg), tag="results",
            )

            self.logger.info(f"dnsperf ran succesfully!\n")

    def parse_process_output(self, stdout: str) -> DnsperfStdout:
        """Parse string output from the dnsperf benchmark."""

        output_parser = ttp(data=stdout, template=self.output_template)
        output_parser.parse()
        result = output_parser.result()[0][0]
        result["config"]["start_time"] = dateutil.parser.parse(result["config"]["start_time"])
        return DnsperfStdout(
            **result["stats"],
            **result["config"],
            throughput_ts=tuple(ThroughputSample(**item) for item in result["data"] if "throughput" in item),
            rtt_samples=tuple(DnsRttSample(**item) for item in result["data"] if "throughput" not in item),
        )
