#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test functionality in the process module."""
import logging
import shlex
import subprocess

import pytest

import snafu.process


class TestLiveProcess:
    """Test the LiveProcess context manager."""

    @staticmethod
    def test_check_pipes_method_only_modifies_if_no_user_given_values():
        """Test that LiveProcess._check_pipes only modifies pipes in kwargs if user didn't specify pipes."""

        for key in ("stdout", "stderr", "capture_output"):
            kwargs = {key: True}
            proc = snafu.process.LiveProcess("", **kwargs)
            assert proc.kwargs == {key: True}

        kwargs = {}
        proc = snafu.process.LiveProcess("")
        assert proc.kwargs.get("stdout", None) is not None and proc.kwargs.get("stderr", None) is not None

    @staticmethod
    def test_live_process_calls_start_on_enter_and_cleanup_on_exit(monkeypatch):
        """Test that when we enter the LiveProcess CM we call start, and on exit we call cleanup."""

        def monkey_start(self):
            self.monkey_start = True

        def monkey_cleanup(self):
            self.monkey_cleanup = True

        monkeypatch.setattr("snafu.process.LiveProcess.start", monkey_start)
        monkeypatch.setattr("snafu.process.LiveProcess.cleanup", monkey_cleanup)

        with snafu.process.LiveProcess("") as proc:
            assert proc.monkey_start is True
        assert proc.monkey_cleanup is True

    @staticmethod
    def test_live_process_runs_a_command_and_gives_output():
        """Test that LiveProcess can run a process and give us the expected process information."""

        tests = (
            (
                {"cmd": shlex.split("echo test")},
                {"stdout": "test\n", "stderr": "", "rc": 0, "time_seconds": [0, 0.2]},
            ),
            (
                {"cmd": "echo 'test'; sleep 0.5; echo 'test2'", "shell": True},
                {"stdout": "test\ntest2\n", "stderr": "", "rc": 0, "time_seconds": [0.5, 1]},
            ),
            (
                {"cmd": "echo 'test' >&2 | grep 'not here'", "shell": True},
                {"stdout": "", "stderr": "test\n", "rc": 1, "time_seconds": [0, 0.2]},
            ),
            (
                {"cmd": "echo 'test' >&2", "shell": True, "stderr": subprocess.STDOUT},
                {"stdout": "", "stderr": "", "rc": 0, "time_seconds": [0, 0.2]},
            ),
            (
                {
                    "cmd": "echo 'test' >&2",
                    "shell": True,
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.STDOUT,
                },
                {"stdout": "test\n", "stderr": "", "rc": 0, "time_seconds": [0, 0.2]},
            ),
        )

        for kwargs, results in tests:
            with snafu.process.LiveProcess(**kwargs) as proc:
                pass

            attempt = proc.attempt
            for key, val in results.items():
                if key == "time_seconds":
                    assert val[0] < attempt.time_seconds < val[1]
                else:
                    assert getattr(attempt, key) == val

    @staticmethod
    def test_live_process_kills_and_does_cleanup_after_timeout():
        """Test that LiveProcess will only kill a process after a timeout."""

        with snafu.process.LiveProcess(shlex.split("sleep 0.5"), timeout=1) as proc:
            pass
        assert 0 < proc.attempt.time_seconds < 1
        assert proc.attempt.hit_timeout is False

        with snafu.process.LiveProcess(shlex.split("sleep 2"), timeout=0.5) as proc:
            pass
        assert 0 < proc.attempt.time_seconds < 1
        assert proc.attempt.hit_timeout is True


def test_get_process_sample_will_use_live_process(monkeypatch):
    """Assert that get_process_sample will use LiveProcess in the background."""

    class MyError(Exception):  # pylint: disable=C0115
        pass

    def live_process_monkey(*args, **kwargs):
        raise MyError

    monkeypatch.setattr("snafu.process.LiveProcess", live_process_monkey)
    with pytest.raises(MyError):
        snafu.process.get_process_sample("TEST_USES_LIVE_PROCESS", logging.getLogger())


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
