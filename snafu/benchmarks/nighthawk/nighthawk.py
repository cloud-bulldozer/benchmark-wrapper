#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the nighthawk workload. See https://github.com/envoyproxy/nighthawk for more information."""
import dataclasses
import datetime
import re
import shlex
import sys
import json
import os
import socket
import numpy as np
import subprocess
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import Config, ConfigArgument, FuncAction, check_file, none_or_type


@dataclasses.dataclass
class NighthawkStat:
    """Parsed Nighthawk Statistic."""

    requested_qps: float
    actual_qps: float
    throughput: float
    status_codes: dict()
    p50_latency: float
    p75_latency: float
    p80_latency: float
    p90_latency: float
    p95_latency: float
    p99_latency: float
    p99_9_latency: float
    avg_latency: float
    timestamp: str
    bytes_in: float
    bytes_out: float
    iteration: Optional[int] = None


@dataclasses.dataclass
class NighthawkOut:
    """Parsed Nighthawk Final Output."""

    workload: str
    uuid: str
    user: str
    cluster_name: str
    duration: str
    targets: List[str]
    execution_results: NighthawkStat
    concurrency: int
    connections: int
    max_requests_per_connection: int
    hostname: str


@dataclasses.dataclass
class NighthawkConfig:
    """Container for common configuration options that are passed to Nighthawk."""

    concurrency: Optional[int] = None
    duration: Optional[int] = None
    connections: Optional[int] = None
    max_requests_per_connection: Optional[int] = None
    rps: Optional[int] = None
    kind: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def new(cls, stdout: NighthawkStat, config: Config):
        """Create a new instance given instances of :py:mod:`~snafu.config.Config` and NighthawkStat."""

        kwargs: Dict[str, Any] = {}
        for fields in dataclasses.fields(cls):
            val = getattr(stdout, fields.name, None)
            if val is None:
                val = getattr(config, fields.name, None)
            kwargs[fields.name] = val
        return cls(**kwargs)


class Nighthawk(Benchmark):
    """Wrapper for the nighthawk benchmark."""

    tool_name = "nighthawk"
    args = (
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
        ConfigArgument(
            "--url",
            dest="url",
            env_var="URL",
            help="Provide the url to make hits",
            required=True,
        ),
        ConfigArgument(
            "--rps", 
            dest="rps", 
            env_var="RPS", 
            help="The target requests-per-second rate", 
            default=5, 
            type=int),
        ConfigArgument(
            "--max_requests_per_connection", 
            dest="max_requests_per_connection", 
            env_var="MAX_REQUESTS_PER_CONNECTION", 
            help="Max requests per connection",
            default=4294937295, 
            type=int),
        ConfigArgument(
            "--connections", 
            dest="connections", 
            env_var="CONNECTIONS", 
            help="The maximum allowed number of concurrent connections per event loop",
            default=100, 
            type=int),
        ConfigArgument(
            "--duration", 
            dest="duration", 
            env_var="DURATION", 
            help="The number of seconds that the test should run", 
            default=60, 
            type=int),
        ConfigArgument(
            "--concurrency", 
            dest="concurrency", 
            env_var="CONCURRENCY", 
            help="The number of concurrent event loops that should be used. Specify 'auto' to "\
                "let Nighthawk leverage all vCPUs that have affinity to the Nighthawk process"\
                ". Note that increasing this results in an effective load multiplier combined"\
                " with the configured --rps and --connections values", 
            default=1, 
            type=int),
    )

    def setup(self) -> bool:
        """Parse config and check for validations."""
        self.config.parse_args()
        self.logger.debug(f"Got config: {vars(self.config)}")

        if not getattr(self.config, "user", False) or not getattr(self.config, "uuid", False):
            self.logger.critical("Missing required metadata. Need both user and uuid to continue")
            return False

        return True

    def _parse_stdout(self) -> NighthawkStat:
        """
        Return parsed stdout of Nighthawk sample.

        Returns
        -------
        NighthawkStat
        """

        data = json.load(open("nighthawk.json"))
        # populating latency in milliseconds and throughput as queries per second.
        latency_percentiles = {}
        duration_histogram = data['DurationHistogram']
        for each_percentile in duration_histogram['Percentiles']:
            percentile = str(each_percentile['Percentile'])
            if percentile not in latency_percentiles.keys():
                latency_percentiles[percentile] = 0
            latency_percentiles[percentile] += each_percentile['Value'] * 1000

        return NighthawkStat(
            requested_qps=data['RequestedQPS'],
            actual_qps=data["ActualQPS"], 
            throughput=data["ActualQPS"],
            status_codes=data["RetCodes"],
            p50_latency=latency_percentiles.get("50", None),
            p75_latency=latency_percentiles.get("75", None),
            p80_latency=latency_percentiles.get("80", None),
            p90_latency=latency_percentiles.get("90", None),
            p95_latency=latency_percentiles.get("95", None),
            p99_latency=latency_percentiles.get("99", None),
            p99_9_latency=latency_percentiles.get("99.9", None),
            avg_latency=duration_histogram['Avg'] * 1000,
            timestamp=data['StartTime'],
            bytes_in=float(data['BytesReceived']),
            bytes_out=float(data['BytesSent'])
        )

    def _run_nighthawk(self):
        """
        Method to execute nighthawk command.
        """

        cmd = (
            "nighthawk_client --concurrency {0} --duration {1} --connections {2} "
            "--max-requests-per-connection {3} --rps {4} --output-format fortio {5} > nighthawk.json"
        ).format(self.config.concurrency, self.config.duration, self.config.connections, 
                self.config.max_requests_per_connection, self.config.rps, self.config.url)
        self.logger.info(cmd)
        p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.stdout.strip().decode("utf-8"), p.stderr.strip().decode("utf-8"), p.returncode
    
    def _json_payload(self, data, sample):
        """
        Method to return the final nighthawk output of a sample.
        """

        data.iteration = sample
        return NighthawkOut(
            workload="nighthawk",
            uuid=self.config.uuid,
            user=self.config.user,
            cluster_name=os.getenv("clustername", "mycluster"),
            duration=self.config.duration,
            targets=[self.config.url],
            execution_results=data,
            concurrency=self.config.concurrency,
            connections=self.config.connections,
            max_requests_per_connection=self.config.max_requests_per_connection,
            hostname=socket.gethostname()
        )

    def collect(self) -> Iterable[BenchmarkResult]:
        """
        Run nighthawk benchmark ``self.config.sample`` number of times.

        Returns immediately if a sample fails. Will attempt to Nighthawk run for each sample.
        """

        cmd = shlex.split(f"nighthawk_client --concurrency {self.config.concurrency} --duration {self.config.duration} --connections {self.config.connections} --max-requests-per-connection {self.config.max_requests_per_connection} --rps {self.config.rps} --output-format fortio {self.config.url} > nighthawk.json")
        _plural = "s" if self.config.sample > 1 else ""
        self.logger.info(f"Collecting {self.config.sample} sample{_plural} of Nighthawk")

        for s in range(1, self.config.sample + 1):

            self.logger.info("Starting nighthawk sample %d out of %d with uuid %s" % (s, self.config.sample, self.config.uuid))
            stdout, stderr, rc = self._run_nighthawk()
            if rc:
                self.logger.critical("Nighthawk failed with returncode %d, stopping benchmark" % rc)
                self.logger.critical("stdout: %s" % stdout)
                self.logger.critical("stderr: %s" % stderr)
                exit(1)
            parsed_data: NighthawkStat = self._parse_stdout()
            es_data: NighthawkOut = self._json_payload(parsed_data, s)
            config: NighthawkConfig = NighthawkConfig.new(parsed_data, self.config)
            result: BenchmarkResult = self.create_new_result(
                data=dataclasses.asdict(es_data),
                config=dataclasses.asdict(config),
                tag="results",
                )
            yield result
            self.logger.info(f"{'-'*50}")
            self.logger.info(f"Got sample result: {result}")
            self.logger.info(f"{'-'*50}")
            self.logger.info("Finished executing nighthawk sample %d out of %d" % (s, self.config.sample))
        self.logger.info(f"Successfully collected {self.config.sample} sample{_plural} of nighthawk.")

    @staticmethod
    def cleanup() -> bool:
        """Nighthawk doesn't have any cleanup tasks, therefore this method just returns ``True``."""
        return True
