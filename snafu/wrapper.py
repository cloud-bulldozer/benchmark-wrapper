#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Implementation of Wrapper base class"""
from typing import Any, Iterable, NewType, Union
from abc import ABC, abstractmethod
import logging
import argparse
import configargparse
from . import registry


JSONMetric = NewType("JSONMetric", dict)


class Wrapper(ABC, metaclass=registry.ToolRegistryMeta):
    """
    Abstract Base class for wrapped external tools.

    Uses the ``registry.ToolRegistryMeta`` metaclass, allowing for each subclass to be added into the
    tool registry automatically.

    Attributes
    ----------
    arg_parser : configargparse.ArgumentParser
        Argument parser that tool-specific arguments can be added onto. Please see
        the "ArgParser Singletons" section of https://pypi.org/project/ConfigArgParse/.
    config : argparse.Namespace
        Parsed config from argument parser. Will be set to ``None`` until populated with
        ``populate_args``.
    logger : logging.Logger
        Python logger for logging messages. Will be named "snafu.<tool_name>".
    """

    tool_name = "_base_wrapper"

    def __init__(self):
        self.arg_parser: configargparse.ArgumentParser = configargparse.get_argument_parser()
        self.config: argparse.Namespace = None
        self.logger = logging.getLogger("snafu").getChild(self.tool_name)

    def populate_args(self) -> None:
        """Use argument parser to parser args and populate ``config`` attribute."""

        self.config = self.arg_parser.parse_args()

    def preflight_checks(self) -> bool:
        """
        Preflight checks to run before setup.

        Can be used to check existence of config params, needed libraries, etc.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if checks fail.
        """

        return True

    def setup(self) -> None:
        """
        Setup step.

        Can be used to create connections to databases, create files on disk, etc.
        """

        pass

    def cleanup(self):
        """
        Cleanup step.

        Can be used to destroy connections to databases, cleanup files on disk, export config files, etc.
        """

        pass


class Benchmark(Wrapper, ABC):
    """
    Abstract Base class for benchmark tools.

    To use, subclass, set the ``tool_name`` attribute, and overwrite the ``emit_metrics`` method.

    Examples
    --------
    >>> from snafu.wrapper import Benchmark
    >>> class MyBenchmark(Benchmark):
    ...     tool_name = "mybenchmark"
    ...     def __init__(self, my_arg: str):
    ...         super().__init__()
    ...         self.my_arg = my_arg
    ...     def emit_metrics(self) -> Iterable[JSONMetric]:
    ...         for x in range(5):
    ...             yield x
    ...
    >>> from snafu.registry import TOOLS
    >>> mybench = TOOLS["mybenchmark"]("arg1")
    >>> mybench.my_arg
    'arg1'
    >>> list(mybench.emit_metrics())
    [0, 1, 2, 3, 4]
    """

    tool_name = "_base_benchmark"

    def __init__(self):
        super(Wrapper, self).__init__()

    def start(self) -> None:
        """Execute the benchmark."""

        pass

    @abstractmethod
    def emit_metrics(self) -> Iterable[JSONMetric]:
        """Yield metrics for export."""
