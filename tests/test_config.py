#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test functionality in the config module."""
import argparse
import os
import stat

import snafu.config


def test_check_file_returns_bool_as_expected(tmpdir):
    """Test that the check_file function will return ``True`` and ``False`` when it is supposed to."""

    tmpdir.chmod(stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    test_file = tmpdir.join("testfile.txt")
    test_file.write("some content")
    test_file_path = test_file.realpath()
    assert test_file.check()

    test_perms = (
        (os.R_OK, stat.S_IREAD),
        (os.R_OK | os.W_OK, stat.S_IREAD | stat.S_IWRITE),
        (os.R_OK | os.W_OK | os.EX_OK, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC),
    )

    with tmpdir.as_cwd():
        for check, perm in test_perms:
            test_file.chmod(0)
            assert snafu.config.check_file(test_file_path, perms=check) is False
            test_file.chmod(perm)
            assert snafu.config.check_file(test_file_path, perms=check) is True


def test_none_or_type_function():
    """Test that the none_or_type function returns function that casts values only when they aren't None."""

    tests = (
        (int, 1),
        (int, "1"),
        (str, "hey"),
        (str, 2),
        (dict, (("a", 1), ("b", 2))),
    )

    for expected_type, value in tests:
        wrapped = snafu.config.none_or_type(expected_type)
        assert wrapped(None) is None
        assert wrapped(value) == expected_type(value)
        assert isinstance(wrapped(value), expected_type)


def test_func_action_class_calls_func_before_saving():
    """Test that the FuncAction argparse action will call func on value before saving to namespace."""

    class MyAction(snafu.config.FuncAction):
        """Action to append string stored at `my_value' to parameter value."""

        my_value = "my-func-worked"

        def func(self, arg: str) -> str:
            """Append my_value to arg."""
            return arg + self.my_value

    parser = argparse.ArgumentParser()
    parser.add_argument("test", action=MyAction)
    args = parser.parse_args(["an-input"])
    assert args.test == "an-input" + MyAction.my_value
