#!/usr/bin/env python3
"""Wrapper for running the nighthawk workload.

See https://github.com/envoyproxy/nighthawk for more information.
"""
import dataclasses
import json
import os
import socket
import subprocess
import sys
from collections.abc import Iterable
from typing import Any

from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import Config, ConfigArgument


@dataclasses.dataclass
class NighthawkStat:
    """Parsed Nighthawk Statistic."""

    workload: str
    uuid: str
    user: str
    cluster_name: str
    duration: int
    targets: list[str]
    concurrency: int
    connections: int
    max_requests_per_connection: int
    hostname: str
    requested_qps: float
    throughput: float
    status_codes_1xx: float
    status_codes_2xx: float
    status_codes_3xx: float
    status_codes_4xx: float
    status_codes_5xx: float
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
    iteration: int | None = None


@dataclasses.dataclass
class NighthawkConfig:
    """Container for common configuration options that are passed to Nighthawk."""

    concurrency: int | None = None
    duration: int | None = None
    connections: int | None = None
    max_requests_per_connection: int | None = None
    rps: int | None = None
    kind: str | None = None
    url: str | None = None

    @classmethod
    def new(cls, stdout: NighthawkStat, config: Config):
        """Create a new instance given instances of :py:mod:`~snafu.config.Config` and NighthawkStat."""

        kwargs: dict[str, Any] = {}
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
            "--samples",
            dest="samples",
            env_var="SAMPLES",
            default=1,
            type=int,
            help="Number of times to run the benchmark",
            required=True,
        ),
        ConfigArgument(
            "--resourcetype",
            dest="kind",
            env_var="RESOURCETYPE",
            help="Provide the resource type for nighthawk run - pod/vm/baremetal",
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
            type=int,
        ),
        ConfigArgument(
            "--max_requests_per_connection",
            dest="max_requests_per_connection",
            env_var="MAX_REQUESTS_PER_CONNECTION",
            help="Max requests per connection",
            default=4294937295,
            type=int,
        ),
        ConfigArgument(
            "--connections",
            dest="connections",
            env_var="CONNECTIONS",
            help="The maximum allowed number of concurrent connections per event loop",
            default=100,
            type=int,
        ),
        ConfigArgument(
            "--duration",
            dest="duration",
            env_var="DURATION",
            help="The number of seconds that the test should run",
            default=60,
            type=int,
        ),
        ConfigArgument(
            "--concurrency",
            dest="concurrency",
            env_var="CONCURRENCY",
            help="The number of concurrent event loops that should be used. Specify 'auto' to "
            "let Nighthawk leverage all vCPUs that have affinity to the Nighthawk process"
            ". Note that increasing this results in an effective load multiplier combined"
            " with the configured --rps and --connections values",
            default=1,
            type=int,
        ),
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

        with open("nighthawk.json", encoding="utf-8") as f:
            data = json.load(f)
        # populating latency in milliseconds and throughput as queries per second.
        latency_percentiles: dict[str, float] = {}
        duration_histogram = data["DurationHistogram"]
        for each_percentile in duration_histogram["Percentiles"]:
            percentile = str(each_percentile["Percentile"])
            if percentile not in latency_percentiles:
                latency_percentiles[percentile] = 0
            latency_percentiles[percentile] += each_percentile["Value"] * 1000

        status_codes = {"1xx": 0, "2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
        for key, value in data["RetCodes"].items():
            status_code = int(key)
            request_count = int(value)
            if 100 <= status_code < 200:
                status_codes["1xx"] += request_count
            elif 200 <= status_code < 300:
                status_codes["2xx"] += request_count
            elif 300 <= status_code < 400:
                status_codes["3xx"] += request_count
            elif 400 <= status_code < 500:
                status_codes["4xx"] += request_count
            else:
                status_codes["5xx"] += request_count

        return NighthawkStat(
            workload="nighthawk",
            uuid=self.config.uuid,
            user=self.config.user,
            cluster_name=os.getenv("clustername", "mycluster"),
            duration=int(self.config.duration),
            targets=[self.config.url],
            concurrency=self.config.concurrency,
            connections=self.config.connections,
            max_requests_per_connection=self.config.max_requests_per_connection,
            hostname=socket.gethostname(),
            requested_qps=data["RequestedQPS"],
            throughput=data["ActualQPS"],
            status_codes_1xx=status_codes["1xx"],
            status_codes_2xx=status_codes["2xx"],
            status_codes_3xx=status_codes["3xx"],
            status_codes_4xx=status_codes["4xx"],
            status_codes_5xx=status_codes["5xx"],
            p50_latency=latency_percentiles.get("50", None),
            p75_latency=latency_percentiles.get("75", None),
            p80_latency=latency_percentiles.get("80", None),
            p90_latency=latency_percentiles.get("90", None),
            p95_latency=latency_percentiles.get("95", None),
            p99_latency=latency_percentiles.get("99", None),
            p99_9_latency=latency_percentiles.get("99.9", None),
            avg_latency=duration_histogram["Avg"] * 1000,
            timestamp=data["StartTime"],
            bytes_in=float(data["BytesReceived"]),
            bytes_out=float(data["BytesSent"]),
        )

    def _run_nighthawk(self):
        """
        Method to execute nighthawk command.
        """

        cmd = (
            f"nighthawk_client --concurrency {self.config.concurrency} --duration {self.config.duration} "
            f"--connections {self.config.connections} --max-requests-per-connection "
            f"{self.config.max_requests_per_connection} --rps {self.config.rps} "
            f"--output-format fortio {self.config.url} > nighthawk.json"
        )
        self.logger.info(cmd)
        p = subprocess.run(cmd, shell=True, capture_output=True, check=False)
        return p.stdout.strip().decode("utf-8"), p.stderr.strip().decode("utf-8"), p.returncode

    def collect(self) -> Iterable[BenchmarkResult]:
        """
        Run nighthawk benchmark ``self.config.samples`` number of times.

        Returns immediately if a sample fails. Will attempt to Nighthawk run for each sample.
        """

        _plural = "s" if self.config.samples > 1 else ""
        self.logger.info(f"Collecting {self.config.samples} sample{_plural} of Nighthawk")

        for s in range(1, self.config.samples + 1):
            self.logger.info(
                f"Starting nighthawk sample {s} out of {self.config.samples} with uuid {self.config.uuid}"
            )
            stdout, stderr, rc = self._run_nighthawk()
            if rc:
                self.logger.critical(f"Nighthawk failed with returncode {rc}, stopping benchmark")
                self.logger.critical(f"stdout: {stdout}")
                self.logger.critical(f"stderr: {stderr}")
                sys.exit(1)
            parsed_data: NighthawkStat = self._parse_stdout()
            parsed_data.iteration = s
            config: NighthawkConfig = NighthawkConfig.new(parsed_data, self.config)
            result: BenchmarkResult = self.create_new_result(
                data=dataclasses.asdict(parsed_data),
                config=dataclasses.asdict(config),
                tag="results",
            )
            yield result
            self.logger.info(f"{'-' * 50}")
            self.logger.info(f"Got sample result: {result}")
            self.logger.info(f"{'-' * 50}")
            self.logger.info(f"Finished executing nighthawk sample {s} out of {self.config.samples}")
        self.logger.info(f"Successfully collected {self.config.samples} sample{_plural} of nighthawk.")

    def cleanup(self) -> bool:
        """Nighthawk doesn't have any cleanup tasks, therefore this method just returns ``True``."""
        return True
