#!/usr/bin/env python3
"""Base benchmark tools."""
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from snafu import registry
from snafu.config import Config, ConfigArgument, FuncAction


@dataclass
class BenchmarkResult:
    """
    Dataclass representation of a Benchmark result.

    Parameters
    ----------
    name : str
        Associated benchmark name
    metadata : dict
        Extra metadata to include with the benchmark result
    config : dict
        Configuration information of the benchmark
    data : dict
        Benchmark result data
    labels : dict
        User-provided labels to add into the benchmark result
    tag : str
        Reference tag to set elasticsearch index
    """

    name: str
    metadata: dict[str, Any]
    config: dict[str, Any]
    data: dict[str, Any]
    labels: dict[str, Any]
    tag: str

    def to_jsonable(self) -> dict[str, Any]:
        """Transform dataclass into exportable JSON doc."""

        result: dict[str, Any] = {}
        result.update(self.config)
        result.update(self.data)
        result.update(self.metadata)
        result.update(self.labels)
        result["workload"] = self.name

        return result


class LabelParserAction(FuncAction):
    """
    argparse action to parse labels in the format of key=value1,key2=value2,... into a dict.

    Raises
    ------
    ValueError
        If given arg isn't formatted correctly
    """

    @staticmethod
    def func(arg: str) -> dict[str, str]:
        """Parse given arg by splitting on ',', then on '='."""
        labels = {}
        for pair in arg.strip().split(","):
            pair_split = pair.split("=")

            if len(pair_split) != 2:
                raise ValueError(
                    f"Got invalid format for labels, should be in format key=value,key=value,...: {arg}"
                )
            key, value = pair_split

            labels[key] = value
        return labels


class Benchmark(ABC, metaclass=registry.ToolRegistryMeta):
    """
    Abstract Base class for benchmark tools.

    To use, subclass, set the ``tool_name``, ``args`` and ``metadata`` attributes, and overwrite the
    ``run``, ``cleanup`` and ``setup`` methods.
    """

    tool_name = "_base_benchmark"
    args: Iterable[ConfigArgument] = tuple()
    metadata: Iterable[str] = ["cluster_name", "user", "uuid"]
    _common_args: Iterable[ConfigArgument] = (
        ConfigArgument(
            "-l",
            "--labels",
            help="Extra labels to add in results exported by benchmark. Format: key1=value1,key2=value2,...",
            dest="labels",
            default={},
            action=LabelParserAction,
        ),
        ConfigArgument("--cluster-name", dest="cluster_name", env_var="clustername", default=None),
        ConfigArgument("--user", dest="user", env_var="test_user", help="Provide user", default=None),
        ConfigArgument(
            "-u", "--uuid", dest="uuid", env_var="uuid", help="Provide UUID for run", default=None
        ),
    )

    def __init__(self):
        self.logger: logging.Logger = logging.getLogger("snafu").getChild(self.tool_name)
        self.config = Config(self.tool_name)
        self.config.populate_parser(self._common_args)
        self.config.populate_parser(self.args)

    def get_metadata(self) -> dict[str, str]:
        """
        Get metadata dictionary

        Uses the metadata attribute as a list of keys to pull from the config.
        """

        metadata: dict[str, str] = {}
        for key in self.metadata:
            value = getattr(self.config, key, None)
            if value is not None:
                metadata[key] = value
        return metadata

    def create_new_result(self, data: dict[str, Any], config: dict[str, Any], tag: str) -> BenchmarkResult:
        """Shortcut method for creating a new :py:class:`BenchmarkResult` instance."""
        result = BenchmarkResult(
            name=self.tool_name,
            labels=self.config.labels,
            metadata=self.get_metadata(),
            tag=tag,
            data=data,
            config=config,
        )
        return result

    @abstractmethod
    def setup(self) -> bool:
        """Setup the benchmark, returning ``False`` if something went wrong."""

    @abstractmethod
    def collect(self) -> Iterable[BenchmarkResult]:
        """Execute the benchmark and return Iterable of BenchmarkResults."""

    @abstractmethod
    def cleanup(self) -> bool:
        """Cleanup the benchmark as needed."""

    def run(self) -> Iterable[BenchmarkResult]:
        """Run setup -> collect -> cleanup. Yield from collect."""

        self.logger.info(f"Starting {self.tool_name} wrapper.")
        self.logger.info("Running setup tasks.")
        if not self.setup():
            self.logger.critical("Something went wrong during setup, refusing to run.")
            return

        self.logger.info("Collecting results from benchmark.")
        yield from self.collect()

        self.logger.info("Cleaning up")
        if not self.cleanup():
            self.logger.critical("Something went wrong during cleanup.")
            return
