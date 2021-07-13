#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Perform functional tests of uperf."""
import shlex
import subprocess


def test_basic_run_of_uperf(manifest):
    """
    Test that we can run a command within the 'uperf' container.

    If this test fails then either the compose file has changed or something went wrong starting
    the container.
    """

    result = subprocess.run(
        shlex.split(f"{manifest.format(container='uperf-test-pod-uperf')} echo 'Hello World'"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    result_stdout = result.stdout.decode("utf-8")
    assert "Hello World" in result_stdout
