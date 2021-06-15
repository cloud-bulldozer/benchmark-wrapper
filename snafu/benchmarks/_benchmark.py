#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base benchmark tools."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable
from dataclasses import dataclass
import logging
import json
from snafu import registry
from snafu.config import Config, ConfigArgument


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


class Benchmark(ABC, metaclass=registry.ToolRegistryMeta):
    """
    Abstract Base class for benchmark tools.

    To use, subclass, set the ``tool_name`` attribute, and overwrite the ``run`` method.
    """

    tool_name = "_base_benchmark"
    args: Iterable[ConfigArgument] = tuple()

    def __init__(self, metadata: Dict[str, str] = None):
        self.metadata: Dict[str, str] = metadata if metadata is not None else dict()
        self.logger: logging.Logger = logging.getLogger("snafu").getChild(self.tool_name)
        self.config = Config(self.tool_name)
        self.config.populate_parser(self.args)

    def create_new_result(
        self, data: Dict[str, Any], config: Dict[str, Any], extra_metadata: Dict[str, Any], label: str
    ) -> BenchmarkResult:
        metadata = self.metadata
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
