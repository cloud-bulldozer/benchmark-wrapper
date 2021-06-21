#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for setting up config arguments."""
import os
from typing import Any, Iterable, List, Mapping
import argparse
import configargparse

# TODO: Add ability to create dependent args that are only required when another arg is given


def check_file(file: str, perms: int = None) -> bool:
    """
    Check that the given file (relative or absolute dir) exists and has the given minimum permissions.
    Given ``perms`` should be combination of ``os.R_OK``, ``os.W_OK`` and ``os.X_OK``. By default
    will just check if the file is readable.
    """

    if perms is None:
        perms = os.R_OK
    perms |= os.F_OK
    return os.access(os.path.abspath(file), perms)


class FuncAction(argparse.Action):
    """argparse Action to run a function on an arg before storing it."""

    def func(self, arg: Any) -> Any:
        """Overwrite me."""

    def __call__(
        self,
        parser: configargparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string=None,
    ):
        setattr(namespace, self.dest, self.func(values))


class ConfigArgument:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class Config:
    """
    Class for managing config parameters.

    Uses argparse and configargparse in the background
    """

    def __init__(self, tool_name: str):
        self.params: argparse.Namespace = argparse.Namespace()
        self.parser: configargparse.ArgumentParser = configargparse.get_argument_parser()
        self.group = self.parser.add_argument_group(tool_name)
        self.env_to_params: Mapping[str, str] = dict()

    def __getattr__(self, attr):
        return getattr(self.params, attr, None)

    def add_argument(self, *args, **kwargs) -> None:
        """Add argument into the config. Uses arg and kwarg format of argparse.add_argument."""

        action = self.group.add_argument(*args, **kwargs)
        env_var = getattr(action, "env_var", None)
        if env_var is not None:
            self.env_to_params[env_var] = action.dest

    def populate_parser(self, args: Iterable[ConfigArgument]) -> None:
        """Populate args in parser from given args list."""

        for arg in args:
            self.add_argument(*arg.args, **arg.kwargs)

    def parse_args(self, args: List[str] = None) -> None:
        """Parse arguments and set values in ``config`` attribute."""

        self.parser.parse_known_args(args=args, namespace=self.params)
