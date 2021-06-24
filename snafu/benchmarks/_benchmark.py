#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base benchmark tools."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable
from dataclasses import dataclass
import logging
from snafu import registry
from snafu.config import Config, ConfigArgument, FuncAction


@dataclass
class BenchmarkResult:
    name: str
    metadata: Dict[str, Any]
    config: Dict[str, Any]
    data: Dict[str, Any]
    label: str

    def to_jsonable(self) -> Dict[str, Any]:
        result: Dict[str, Any] = dict()
        result.update(self.config)
        result.update(self.data)
        result["benchmark"] = self.name
        result["metadata"] = self.metadata

        return result


class LabelParserAction(FuncAction):
    """argparse action to parse labels in the format of key=value1,key2=value2,... into a dict"""

    def func(self, arg: str) -> Dict[str, str]:
        labels = dict()
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

    To use, subclass, set the ``tool_name`` and ``args`` attribute, and overwrite the ``run``, ``cleanup`` and
    ``setup`` methods.
    """

    tool_name = "_base_benchmark"
    args: Iterable[ConfigArgument] = tuple()
    _common_args: Iterable[ConfigArgument] = (
        ConfigArgument(
            "-l",
            "--labels",
            help="Metadata to add in results exported by benchmark. Format: key1=value1,key2=value2,...",
            dest="labels",
            action=LabelParserAction,
        ),
    )

    def __init__(self):
        self.logger: logging.Logger = logging.getLogger("snafu").getChild(self.tool_name)
        self.config = Config(self.tool_name)
        self.config.populate_parser(self._common_args)
        self.config.populate_parser(self.args)

    def create_new_result(self, data: Dict[str, Any], config: Dict[str, Any], label: str) -> BenchmarkResult:

        result = BenchmarkResult(
            name=self.tool_name, metadata=self.config.labels, data=data, config=config, label=label,
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
            self.logger.critical(f"Something went wrong during setup, refusing to run.")
            return

        self.logger.info(f"Collecting results from benchmark.")
        yield from self.collect()

        self.logger.info(f"Cleaning up")
        if not self.cleanup():
            self.logger.critical(f"Something went wrong during cleanup.")
            return
