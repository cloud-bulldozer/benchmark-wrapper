#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the dnsperf benchmark.
See https://dns-oarc.net/tools/dnsperf for more information."""
import datetime
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

import dateutil.parser
import dateutil.tz
import pandas as pd
import toolz
from pydantic import BaseModel
from ttp import ttp

from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import ConfigArgument
from snafu.process import ProcessSample, get_process_sample

Number = Union[int, float]


class DnsRttSample(BaseModel):
    """DNS query domain name, round trip time, type, response state.
    The response state is either a DNS response code supported by
    dnsperf, or a 'T' for timeout."""

    fqdn: str
    rtt_s: float
    qtype: str
    response_state: str


class DnsperfSummary(BaseModel):
    """The summary statistics from a dnsperf execution."""

    throughput_mean: float
    queries_sent: int
    queries_completed: int
    runtime_length: float
    rtt_sum: float
    load_mean: Optional[float] = None

    class Config:
        """Pydantic custom configuration."""

        validate_assignment = True
        allow_mutation = True

    def summarize(self):
        """Calculate remaining statistics from benchmark data."""
        self.load_mean = self.queries_sent / self.runtime_length


class DnsperfMetadata(BaseModel):
    """Metadata to (re)create a dnsperf execution."""

    address: str
    cache_negative_size: int
    cache_positive_size: int
    client_threads: int
    dnsperf_version: str
    end_time: datetime.datetime
    # the load limit number is parsed to a string,
    # so that it can be stored as a discrete
    # variable; one possible value is infinity;
    # JSON doesn't like "Infinity" when it expects a number
    load_limit: str
    port: int
    start_time: datetime.datetime
    timeout_length: float
    transport_mode: str
    cluster_name: Optional[str] = None
    platform: Optional[str] = None
    networkpolicy: Optional[str] = None
    node_id: Optional[str] = None
    network_type: Optional[str] = None
    user: Optional[str] = None
    uuid: Optional[str] = None


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
        ConfigArgument("-l", "--load-sequence", dest="load_sequence", nargs="+", default=[]),
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
            "-p",
            "--cache-positive-size",
            help="Size of the positive response (i.e. 'NOERROR') cache",
            dest="cache_positive_size",
            default=9984,
        ),
        ConfigArgument(
            "-n",
            "--cache-negative-size",
            help="Size of the negative response (i.e. 'NXDOMAIN') cache",
            dest="cache_negative_size",
            default=9984,
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
        if not self.config.load_sequence:
            self.config.load_sequence.append("inf")
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

    def collect(self) -> Iterable[BenchmarkResult]:
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
            ]

            if isinstance(load_limit, int):
                cmd = [*cmd, "-Q", str(load_limit)]

            process_sample: ProcessSample = get_process_sample(cmd, self.logger)

            if not process_sample.success:
                self.logger.critical(f"dnsperf failed to complete! Got results: {process_sample}\n")
                return
            if process_sample.successful.stdout is None:
                self.logger.critical(
                    "dnsperf ran successfully, but did not get output on stdout.\n"
                    f"Got results: {process_sample}\n"
                )
                return

            metadata: DnsperfMetadata
            rtt_samples: Tuple[DnsRttSample, ...]
            summary: DnsperfSummary
            metadata, summary, rtt_samples = self.parse_process_output(
                process_sample.successful.stdout, load_limit
            )
            summary.summarize()
            dataframe = pd.DataFrame.from_dict([dict(sample) for sample in rtt_samples])

            for sample in dataframe.groupby("fqdn").sample(n=1).to_dict("records"):
                yield self.create_new_result(
                    data=dict(summary, **sample), config=dict(metadata), tag="results"
                )

        self.logger.info("ran succesfully!\n")

    def parse_process_output(
        self, stdout: str, load_limit: Number
    ) -> Tuple[DnsperfMetadata, DnsperfSummary, Tuple[DnsRttSample, ...]]:
        """Parse string output from the dnsperf benchmark."""

        output_parser = ttp(data=stdout, template=self.output_template)
        output_parser.parse()
        result = output_parser.result()[0][0]
        result["config"]["start_time"] = dateutil.parser.parse(result["config"]["start_time"]).astimezone()
        metadata: DnsperfMetadata = DnsperfMetadata(
            **toolz.merge(self.config.params.__dict__, result["config"]),
            end_time=datetime.datetime.now().astimezone(),
            load_limit=str(load_limit),
        )
        data: DnsperfSummary = DnsperfSummary(**result["stats"], **result["config"])
        return metadata, data, tuple(DnsRttSample(**item) for item in result["data"])
