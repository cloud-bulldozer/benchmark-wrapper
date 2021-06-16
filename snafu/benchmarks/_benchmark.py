#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base benchmark tools."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable
from dataclasses import dataclass
import logging
import json
from snafu import registry
from snafu.config import Config, ConfigArgument, FuncAction


@dataclass
class BenchmarkResult:
    name: str
    metadata: Dict[str, Any]
    config: Dict[str, Any]
    data: Dict[str, Any]
    label: str

    def to_json(self) -> str:
        result: Dict[str, Any] = dict()
        result.update(self.config)
        result.update(self.data)
        result["benchmark"] = self.name
        result["metadata"] = self.metadata

        return json.dumps(result)


class LabelParserAction(FuncAction):
    """argparse action to parse labels in the format of key=value1,key2=value2,... into a dict"""

    def func(self, arg: str) -> Dict[str, str]:
        return dict(map(lambda pair: pair.split("="), arg.strip().split(",")))


class Benchmark(ABC, metaclass=registry.ToolRegistryMeta):
    """
    Abstract Base class for benchmark tools.

    To use, subclass, set the ``tool_name`` and ``args`` attribute, and overwrite the ``run`` and
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

    def create_new_result(
        self, data: Dict[str, Any], config: Dict[str, Any], extra_metadata: Dict[str, Any], label: str
    ) -> BenchmarkResult:
        metadata = self.config.labels
        metadata.update(extra_metadata)

        result = BenchmarkResult(
            name=self.tool_name, metadata=metadata, data=data, config=config, label=label
        )
        return result

    @abstractmethod
    def setup(self) -> bool:
        """Setup the benchmark, returning ``False`` if something went wrong."""

    @abstractmethod
    def run(self) -> Iterable[BenchmarkResult]:
        """Execute the benchmark and return Iterable of Metrics."""
