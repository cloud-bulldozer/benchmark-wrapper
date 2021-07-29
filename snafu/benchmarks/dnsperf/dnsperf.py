#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the dnsperf benchmark.
See https://dns-oarc.net/tools/dnsperf for more information."""
from datetime import datetime
from typing import Iterable, Optional, Tuple
from pathlib import Path

import dateutil.parser
from pydantic import BaseModel
from ttp import ttp
import toolz

from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import Config, ConfigArgument
from snafu.process import ProcessSample, sample_process


class RawDnsperfSample(BaseModel):
    fqdn: str
    rtt_mu_s: int
    qtype: str
    rcode: str


class DnsperfStdout(BaseModel):
    avg_request_packet_size: int
    avg_response_packet_size: int
    sum_rtt: float
    queries_sent: int
    queries_completed: int
    throughput: float
    start_time: datetime
    dnsperf_version: str
    time_limit: float
    data: Optional[RawDnsperfSample]


class DnsperfConfig(BaseModel):
    address: str
    port: int
    query_filepath: Path
    start_time: datetime
    sum_rtt: float
    dnsperf_version: str
    # 0 to 10_000
    clients: int
    # [1, +inf)
    time_limit: float
    transport_mode: str
    # [1, +inf]
    max_allowed_load: Optional[float] = None
    cache_size: Optional[int]
    networkpolicy: Optional[str] = None
    pod_id: Optional[str] = None

    @classmethod
    def new(cls, stdout: DnsperfStdout, config: Config, load):
        """
        Merge attributes parsed from stdout and config.
        """
        # merge dictionaries (right-most dictionary takes precedence)
        # then, unpack merged dictionary
        return cls(**toolz.merge(config.params.__dict__, dict(stdout)), max_allowed_load=load)


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
        ConfigArgument("--load-sequence", dest="load_sequence", type=int, nargs="+", default=None),
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
            "-s",
            "--cache-size",
            dest="cache_size",
            env_var="cache_size",
            help="Quantity of entries allowed in cache",
        ),
        ConfigArgument(
            "-l",
            "--time-limit",
            dest="time_limit",
            env_var="time_limit",
            help="Time window size for test",
            default=".01",
        ),
        ConfigArgument(
            "-m",
            "--transport-mode",
            dest="transport_mode",
            help="set transport mode: udp, tcp, dot",
            default="udp",
        ),
        ConfigArgument("--network-policy", dest="networkpolicy", env_var="networkpolicy"),
        ConfigArgument("--pod-id", dest="pod_id", env_var="my_pod_idx", default=None),
    )

    def setup(self) -> bool:
        """Setup dnsperf benchmark."""
        self.logger.info("Setting up dnsperf benchmark.")
        self.config.parse_args()
        self.config.load_sequence.append(None)
        return True

    def cleanup(self) -> bool:
        """Clean up artifacts from the dnsperf benchmark."""
        self.logger.info("Cleaning up dnsperf benchmark.")
        return True

    def collect(self) -> Iterable[BenchmarkResult]:
        """Run the dnsperf benchmark and collect results."""

        self.logger.info("Starting dnsperf")
        for load in self.config.load_sequence:
            cmd = [
                "dnsperf",
                "-v",  # print latency information for each query
                "-s",
                self.config.address,
                "-p",
                self.config.port,
                "-d",
                self.config.query_filepath,
                "-c",
                self.config.clients,
                "-l",
                self.config.time_limit,
                "-m",
                self.config.transport_mode,
            ]

            if load:
                cmd = [*cmd, "-Q", str(load)]

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

            stdout: DnsperfStdout
            samples: Tuple[RawDnsperfSample, ...]
            stdout, samples = self.parse_stdout(sample.successful.stdout)
            cfg: DnsperfConfig = DnsperfConfig.new(stdout, self.config, load=load)
            for sample in samples:
                sample: RawDnsperfSample
                stdout.data = sample
                yield self.create_new_result(data=dict(stdout), config=dict(cfg), tag="results")

    def parse_stdout(self, stdout: str) -> Tuple[DnsperfStdout, Tuple[RawDnsperfSample, ...]]:
        """Return parsed stdout of Dnsperf sample."""

        output_parser = ttp(data=stdout, template=self.output_template)
        output_parser.parse()
        result = output_parser.result()[0][0]
        result["config"]["start_time"] = dateutil.parser.parse(result["config"]["start_time"])
        return DnsperfStdout(**result["stats"], **result["config"]), result["data"]
