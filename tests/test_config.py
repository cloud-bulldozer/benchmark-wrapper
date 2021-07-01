#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test functionality in the config module."""
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
