#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the dnsperf benchmark.
See https://dns-oarc.net/tools/dnsperf for more information."""
import datetime
from typing import Optional, Tuple, Union
from pathlib import Path
import dataclasses

import dateutil.parser
from pydantic import BaseModel
import pydantic.dataclasses
from ttp import ttp
import toolz
import dateutil.tz

from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import Config, ConfigArgument
from snafu.process import ProcessSample, get_process_sample


Number = Union[int, float]


class DnsRttSample(BaseModel):
    fqdn: str
    rtt_s: float
    qtype: str
    response_state: str


class ThroughputSample(BaseModel):
    timestamp: datetime.datetime
    throughput: float

    @pydantic.validator("timestamp", pre="True")
    def parse_utc(cls, value):
        return datetime.datetime.fromtimestamp(float(value))


@pydantic.dataclasses.dataclass
class DnsperfStdout:
    dnsperf_version: str
    queries_sent: int
    queries_completed: int
    # rtt_samples: Tuple[DnsRttSample, ...]
    start_time: datetime.datetime
    sum_rtt: float
    # throughput_ts: Tuple[ThroughputSample, ...]
    throughput_mean: float
    runtime_length: float
    load_mean: Optional[float] = None

    def __post_init_post_parse__(self):
        self.load_mean = self.queries_sent / self.runtime_length


class DnsperfConfig(BaseModel):
    address: str
    port: int
    client_threads: int
    dnsperf_version: str
    query_filepath: str
    runtime_length: float
    timeout_length: float
    transport_mode: str
    # the load limit number is parsed to a string,
    # so that it can be stored as a discrete
    # variable; one possible value is infinity
    load_limit: Optional[float] = float("inf")
    # networkpolicy: Optional[str] = None
    # network_type: Optional[str] = None
    # pod_id: Optional[str] = None
    # node_id: Optional[str] = None

    @classmethod
    def new(cls, stdout: DnsperfStdout, config: Config, load):
        """
        Merge attributes parsed from stdout and config.
        """
        # merge dictionaries (right-most dictionary takes precedence)
        # then, unpack merged dictionary
        return cls(**toolz.merge(config.params.__dict__, dataclasses.asdict(stdout)), load_limit=load)


# @dataclasses.dataclass
class DnsperfMetadata(BaseModel):
    address: str
    client_threads: int
    dnsperf_version: str
    end_time: datetime.datetime
    # the load limit number is parsed to a string,
    # so that it can be stored as a discrete
    # variable; one possible value is infinity;
    # JSON doesn't like "Infinity" when it expects a number
    load_limit: str
    port: int
    queries_sent: int
    queries_completed: int
    runtime_length: float
    start_time: datetime.datetime
    sum_rtt: float
    throughput_mean: float
    timeout_length: float
    transport_mode: str
    cluster_name: Optional[str] = None
    load_mean: Optional[float] = None
    platform: Optional[str] = None
    networkpolicy: Optional[str] = None
    node_id: Optional[str] = None
    network_type: Optional[str] = None
    user: Optional[str] = None
    uuid: Optional[str] = None

    class Config:
        validate_assignment = True
        allow_mutation = True

    def set_load_mean(self):
        self.load_mean = self.queries_sent / self.runtime_length


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
            "--client-threads",
            dest="client_threads",
            help="Quantity of client threads to act as; (1 client : 1 thread).",
            default="1",
        ),
        ConfigArgument(
            "-r",
            "--runtime-length",
            dest="runtime_length",
            help="Length of time dnsperf will create load",
            default=".01",
        ),
        ConfigArgument("--timeout", help="Length of timeout in seconds", dest="timeout_length", default="5"),
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
            f"'rtt_s': {self.config.timeout_length}"
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
                "-c",
                self.config.client_threads,
                "-T",
                self.config.client_threads,
                "-l",
                self.config.runtime_length,
                "-t",
                self.config.timeout_length,
                "-m",
                self.config.transport_mode,
                "-S",
                self.config.throughput_time_interval,
            ]

            if isinstance(load_limit, int):
                cmd = [*cmd, "-Q", str(load_limit)]

            sample: ProcessSample = get_process_sample(cmd, self.logger)

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

            metadata: DnsperfMetadata
            rtt_samples: Tuple[DnsRttSample, ...]
            throughput_ts: Tuple[ThroughputSample, ...]
            metadata, rtt_samples, throughput_ts = self.parse_process_output(
                sample.successful.stdout, load_limit
            )

            rtt_sample: DnsRttSample
            for rtt_sample in rtt_samples:
                yield self.create_new_result(data=dict(rtt_sample), config=dict(metadata), tag="rtt")

            throughput: ThroughputSample
            for throughput in throughput_ts:
                yield self.create_new_result(data=dict(throughput), config=dict(metadata), tag="throughput")

            self.logger.info(f"ran succesfully!\n")

    def parse_process_output(
        self, stdout: str, load_limit: Number
    ) -> Tuple[DnsperfMetadata, Tuple[DnsRttSample, ...], Tuple[ThroughputSample, ...]]:
        """Parse string output from the dnsperf benchmark."""

        output_parser = ttp(data=stdout, template=self.output_template)
        output_parser.parse()
        result = output_parser.result()[0][0]
        result["config"]["start_time"] = dateutil.parser.parse(result["config"]["start_time"]).astimezone()
        metadata: DnsperfMetadata = DnsperfMetadata(
            **toolz.merge(self.config.params.__dict__, result["config"], result["stats"]),
            load_limit=str(load_limit),
            end_time=datetime.datetime.now().astimezone(),
        )
        metadata.set_load_mean()
        return (
            metadata,
            tuple(DnsRttSample(**item) for item in result["data"] if "throughput" not in item),
            tuple(ThroughputSample(**item) for item in result["data"] if "throughput" in item),
        )
