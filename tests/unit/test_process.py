#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test functionality in the process module."""
import logging
import shlex
import subprocess

import pytest

import snafu.process


def test_get_process_sample_will_set_hit_timeout_as_needed():
    """Test that get_process_sample will set the hit_timeout attribute appropriately for a ProcessRun."""

    cmd = 'echo "hello"; sleep 5; echo "test"'
    result: snafu.process.ProcessSample = snafu.process.get_process_sample(
        cmd, logging.getLogger(), shell=True, retries=0, expected_rc=0, timeout=1, stdout=subprocess.PIPE,
    )

    assert result.success is False
    assert result.expected_rc == 0
    assert result.attempts == 1
    assert result.timeout == 1
    assert len(result.failed) == 1
    assert result.successful is None
    assert result.failed[0].stdout == "hello\n"
    assert result.failed[0].stderr is None
    assert result.failed[0].hit_timeout is True
    assert result.failed[0].time_seconds == 1
    assert result.failed[0].rc is None


def test_get_sample_process_captures_output_by_default():
    """Test that get_sample_process will enable stdout and stderr capture by default."""

    cmd = 'echo "hey there!"'
    result: snafu.process.ProcessSample = snafu.process.get_process_sample(
        cmd, logging.getLogger(), shell=True, retries=0
    )
    assert result.successful.stdout == "hey there!\n"

    no_capture_args = {
        "capture_output": False,
        "stdout": None,
        "stderr": None,
    }
    for arg, val in no_capture_args.items():
        print(arg, val)
        result: snafu.process.ProcessSample = snafu.process.get_process_sample(
            cmd, logging.getLogger(), shell=True, retries=0, **{arg: val}
        )
        assert result.successful.stdout is None


def test_get_process_sample_will_rerun_failed_process(tmpdir):
    """
    Test that get_process_sample will rerun a failed process successfully.

    For this test, we'll run the following command three times, expecting it to succeed on the last run:
    ``echo -n "a" >> testfile.txt ; grep "aaa" testfile.txt``.
    """

    test_file = tmpdir.join("testfile.txt")
    test_file_path = test_file.realpath()
    cmd = f'echo -n "a" >> {test_file_path} ; grep "aaa" {test_file_path}'

    result: snafu.process.ProcessSample = snafu.process.get_process_sample(
        cmd, logging.getLogger(), shell=True, retries=2, expected_rc=0
    )

    assert result.success is True
    assert result.expected_rc == 0
    assert result.attempts == 3
    assert result.timeout is None
    assert not any(failed.rc == 0 for failed in result.failed)
    assert result.successful.rc == 0
    assert result.successful.stdout == "aaa\n"


def test_get_process_sample_sets_failed_if_no_tries_succeed():
    """Test that get_process_sample will set the "success" attribute to False if no tries are successful."""

    result: snafu.process.ProcessSample = snafu.process.get_process_sample(
        shlex.split("test 1 == 0"), logging.getLogger(), retries=0, expected_rc=0
    )
    assert result.success is False


def test_sample_process_uses_get_process_sample(monkeypatch):
    """Test that the sample_process function uses get_process_sample in the background."""

    class MyError(Exception):  # pylint: disable=C0115
        pass

    def monkeypatch_get_process_sample(*args, **kwargs):
        raise MyError

    monkeypatch.setattr("snafu.process.get_process_sample", monkeypatch_get_process_sample)
    with pytest.raises(MyError):
        # need to convert to list since sample_process yields
        list(snafu.process.sample_process("TEST_SAMPLE_PROCESS", logging.getLogger()))


def test_sample_process_yields_appropriate_number_of_samples(tmpdir):
    """
    Test that sample_process will yield the expected number of ProcessSample instances.

    Will use the same test methodology as test_get_process_sample_will_rerun_failed_process.
    """

    test_file = tmpdir.join("testfile.txt")
    test_file_path = test_file.realpath()
    cmd = f'echo -n "a" >> {test_file_path} ; grep "aaa" {test_file_path}'

    samples = snafu.process.sample_process(
        cmd, logging.getLogger(), shell=True, retries=0, expected_rc=0, num_samples=3, timeout=10
    )
    for i, sample in enumerate(samples):
        if i == 2:
            assert sample.success is True
            assert sample.expected_rc == 0
            assert sample.attempts == 1
            assert sample.timeout == 10
            assert len(sample.failed) == 0
            assert sample.successful.hit_timeout is False
            assert sample.successful.rc == 0
            assert sample.successful.stdout == "aaa\n"
        else:
            assert sample.success is False
            assert sample.expected_rc == 0
            assert sample.attempts == 1
            assert sample.timeout == 10
            assert len(sample.failed) == 1
            assert sample.failed[0].rc == 1
