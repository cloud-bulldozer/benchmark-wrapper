#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for wrapping external tools."""
import os
from typing import Any, Dict, Iterable, List, NewType, Set, Tuple
from abc import ABC, abstractmethod
import datetime
import logging
import subprocess
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
    required_args : iterable, optional
        Iterable of required arguments. Will check for these values in ``config`` during preflight_checks.

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
    required_args : set
        Set of required args given during instance creation.
    logger : logging.Logger
        Python logger for logging messages. Will be named "snafu.<tool_name>".
    """

    tool_name = "_base_wrapper"

    def __init__(self, config: Dict[str, Any] = None, required_args: Iterable[str] = None):
        self.arg_parser: configargparse.ArgumentParser = configargparse.get_argument_parser()
        self.arg_group = self.arg_parser.add_argument_group(self.tool_name)
        self.config: argparse.Namespace = argparse.Namespace()
        if config is not None:
            self.config.__dict__.update(config)
        self.required_args: Set[str] = set(required_args) if required_args is not None else set()
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

        self.logger.debug("Parsing args using argparse.")
        self.arg_parser.parse_known_args(args=args, namespace=self.config)
        self.logger.debug(f"Final config: {vars(self.config)}")

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

        self.logger.debug(f"Checking for the following required args: {', '.join(self.required_args)}")
        known_args = self.config.__dict__.keys()
        for arg in self.required_args:
            if arg not in known_args:
                self.logger.warning(f"Missing config argument {arg}!")
                return False
        return True

    def check_file(self, file: str, perms: int = None) -> bool:
        """
        Check that the given file (relative or absolute dir) exists and has the given minimum permissions.
        Given ``perms`` should be combination of ``os.R_OK``, ``os.W_OK`` and ``os.X_OK``. By default
        will just check if the file is readable.

        Returns
        -------
        bool
            ``True`` if the file exists and has min perms, ``False`` otherwise

        Examples
        --------
        >>> from snafu.wrapper import Wrapper
        >>> class MyTool(Wrapper):
        ...     tool_name = "my_tool"
        ...
        ...     def __init__(self):
        ...         super().__init__()
        >>> mytool = MyTool()
        >>> mytool.check_file(os.path.join(__file__))
        True
        """

        if perms is None:
            perms = os.R_OK
        perms |= os.F_OK
        return os.access(os.path.abspath(file), perms)

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

    To use, subclass, set the ``tool_name`` attribute, and overwrite the ``emit_metrics`` and ``run`` methods.

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
    ...     def run(self):
    ...         pass
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

    @staticmethod
    def _run_process(cmd: str) -> Tuple[str, str, int]:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), stderr.strip().decode("utf-8"), process.returncode

    def run_process(self, cmd: str, retries: int = 0, time: bool = False, expected_rc: int = 0) -> Dict:
        """
        Run the given command as a subprocess within a shell and return information about the run within
        a dict.

        Arguments
        ---------
        cmd : str
            Command to run. On each failed attempt, a dict containing metadata will be appended to the list
            at 'failed' key. stdout, stderr and return code will be saved in "stdout", "stderr" and "rc"
            keys respectively. On the successful attempt, each key will be stored in the returnd
            dict itself. If stdout or stderr is empty, then it will not be returned.
        retries : int, optional
            Number of retries for running the command. Will run the command once, check return code, then
            re-run ``retries`` number of times. Defaults to 0. For each attempt, attempt number will be
            stored in "attempt" key and expected return code will be stored in "expected_rc".
        time : bool, optional
            If True, will time execution and return number of seconds it command took to run.
            Defaults to False. Run time will be saved in the "elapsed_seconds" key for each attempt.
        expected_rc : int, optional
            Expected return code of command. Defaults to 0.

        Examples
        --------
        >>> from pprint import pprint # for doctest
        >>> import random
        >>> from snafu.wrapper import Benchmark
        >>> class MyBenchmark(Benchmark):
        ...     tool_name = "mybenchmark"
        ...     def __init__(self):
        ...         super().__init__()
        ...     def run(self):
        ...         pass
        ...     def emit_metrics(self):
        ...         yield dict()
        >>> mybench = MyBenchmark()
        >>> pprint(mybench.run_process("echo 'Hello World'"))
        {'attempt': 1, 'expected_rc': 0, 'rc': 0, 'stdout': 'Hello World'}
        >>> int(mybench.run_process("sleep 1", time=True)['elapsed_seconds'])
        1
        >>> pprint(mybench.run_process("echo 'test' | grep 'hello'", expected_rc=1))
        {'attempt': 1, 'expected_rc': 1, 'rc': 1}
        >>> fn = random.randint(1, 10)
        >>> pprint(mybench.run_process(f"echo -n 'test' >> /tmp/{fn}; grep -w testtest /tmp/{fn}", retries=1))
        {'attempt': 2,
         'expected_rc': 0,
         'failed': [{'attempt': 1, 'expected_rc': 0, 'rc': 1}],
         'rc': 0,
         'stdout': 'testtest'}
        >>> pprint(mybench.run_process(f"rm /tmp/{fn}"))
        {'attempt': 1, 'expected_rc': 0, 'rc': 0}
        """

        self.logger.info(f"Running command {cmd}")
        result: Dict[str, Any] = dict()

        tries: int = 0

        while tries <= retries:
            tries += 1
            self.logger.debug(f"On try {tries}")
            attempt: Dict[str, Any] = dict()

            if time:
                start_time = datetime.datetime.utcnow()

            stdout, stderr, rc = self._run_process(cmd)

            if time:
                end_time = datetime.datetime.utcnow()
                diff_seconds = (end_time - start_time).total_seconds()
                self.logger.debug(f"Run time: {diff_seconds} seconds")

            # only add if not empty
            for key, val in [("stdout", stdout), ("stderr", stderr)]:
                if len(val) > 0:
                    attempt[key] = val
            attempt["rc"] = rc
            attempt["expected_rc"] = expected_rc
            attempt["attempt"] = tries
            if time:
                attempt["elapsed_seconds"] = diff_seconds

            self.logger.debug(f"Got return code {rc}, expected {expected_rc}")
            if rc == expected_rc:
                self.logger.info(f"Command successful!")
                result.update(attempt)
                break
            else:
                self.logger.info(f"Command unsuccessful")
                if result.get("failed", None) is None:
                    result["failed"] = [attempt]
                else:
                    result["failed"].append(attempt)
        else:
            # If we hit retry limit, we go here
            self.logger.info(f"Tried running command {tries} times, with no success.")

        return result

    @abstractmethod
    def run(self) -> None:
        """Execute the benchmark."""

    @abstractmethod
    def emit_metrics(self) -> Iterable[JSONMetric]:
        """Yield metrics for export."""
