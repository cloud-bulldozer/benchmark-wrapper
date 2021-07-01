#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test functionality in the process module."""
import shlex
import subprocess

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
