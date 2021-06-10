#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Implementation of Wrapper base class"""
from typing import Any, Dict, Iterable, List, NewType
from abc import ABC, abstractmethod
import logging
import argparse
import configargparse
from snafu import registry


JSONMetric = NewType("JSONMetric", dict)


class Wrapper(ABC, metaclass=registry.ToolRegistryMeta):
    """
    Abstract Base class for wrapped external tools.

    Uses the ``registry.ToolRegistryMeta`` metaclass, allowing for each subclass to be added into the
    tool registry automatically.

    Parameters
    ----------
    config : dict, optional
        Initial config for tool. Given value should be dict of key-value pairs, where keys are strings.
    required_args : list of str, optional
        List of required arguments. Will check for these values in ``config`` during preflight_checks.

    Attributes
    ----------
    arg_parser : configargparse.ArgumentParser
        Argument parser that tool-specific arguments can be added onto. Please see
        the "ArgParser Singletons" section of https://pypi.org/project/ConfigArgParse/.
    arg_group
        Argument group for the wrapped tool. Use this object when adding arguments to be parsed, then
        parse using ``arg_parser``.
    config : argparse.Namespace
        Parsed config from argument parser. Will be set to ``None`` until populated with
        ``populate_args``.
    logger : logging.Logger
        Python logger for logging messages. Will be named "snafu.<tool_name>".
    """

    tool_name = "_base_wrapper"

    def __init__(self, config: Dict[str, Any] = None, required_args: List[str] = None):
        self.arg_parser: configargparse.ArgumentParser = configargparse.get_argument_parser()
        self.arg_group = self.arg_parser.add_argument_group(self.tool_name)
        self.config: argparse.Namespace = argparse.Namespace()
        if config is not None:
            self.config.__dict__.update(config)
        self.required_args: List[str] = required_args if required_args is not None else list()
        self.logger: logging.Logger = logging.getLogger("snafu").getChild(self.tool_name)

    def parse_args(self, args: List[str] = None) -> None:
        """
        Use argument parser to parse args and set attributes in config namespace.

        Will update ``config`` with the attributes of the ``argparse.Namespace`` pulled from the argument
        parser. For more information on this, see the ``namespace`` argument of
        ``argparse.ArgumentParser.parse_known_args``

        Examples
        --------
        >>> from snafu.wrapper import Wrapper
        >>> class MyTool(Wrapper):
        ...     tool_name = "my_tool"
        ...
        ...     def __init__(self):
        ...         super().__init__(config={"arg1": "one", "arg2": "override me"})
        ...         self.arg_group.add_argument("--arg2")
        ...
        >>> mytool = MyTool()
        >>> vars(mytool.config)
        {'arg1': 'one', 'arg2': 'override me'}
        >>> mytool.parse_args(args=['--arg2', 'two'])
        >>> vars(mytool.config)
        {'arg1': 'one', 'arg2': 'two'}
        """

        self.arg_parser.parse_known_args(args=args, namespace=self.config)

    def check_required_args(self) -> bool:
        """
        Check that all required args are present in config

        Returns
        -------
        bool
            ``True`` on success, ``False`` if a required arg is not present.

        Examples
        --------
        >>> from snafu.wrapper import Wrapper
        >>> class MyTool(Wrapper):
        ...     tool_name = "my_tool"
        ...
        ...     def __init__(self):
        ...         super().__init__(required_args=["arg1"])
        ...         self.arg_group.add_argument("--arg1")
        ...
        >>> mytool = MyTool()
        >>> vars(mytool.config)
        {}
        >>> mytool.check_required_args()
        False
        >>> mytool.parse_args(args=['--arg1', 'one'])
        >>> vars(mytool.config)
        {'arg1': 'one'}
        >>> mytool.check_required_args()
        True
        """

        known_args = self.config.__dict__.keys()
        for arg in self.required_args:
            if arg not in known_args:
                return False
        return True

    def preflight_checks(self) -> bool:
        """
        Preflight checks to run before setup. By default runs ``check_required_args``.

        Can be used to check existence of config params, needed libraries, etc.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if checks fail.
        """

        return self.check_required_args()

    def setup(self) -> None:
        """
        Setup step for ensuring external tool is ready to go.

        Can be used to create connections to databases, create files on disk, etc.
        """

        pass

    def cleanup(self):
        """
        Cleanup step for wrapping up usage of external tool.

        Can be used to clean connections, cleanup files on disk, export config files, etc.
        """

        pass


class Benchmark(Wrapper, ABC):
    """
    Abstract Base class for benchmark tools.

    To use, subclass, set the ``tool_name`` attribute, and overwrite the ``emit_metrics`` method.

    Parameters
    ----------
    metadata : list of str
        List of common metadata that should be exported into JSON payload. Subclasses should implement
        logic to include these config key names in their exported documents. Store as ``metadata``
        attribute

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

    def __init__(self, metadata: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.metadata: List[str] = metadata if metadata is not None else list()

    def run(self) -> None:
        """Execute the benchmark."""

    @abstractmethod
    def emit_metrics(self) -> Iterable[JSONMetric]:
        """Yield metrics for export."""
