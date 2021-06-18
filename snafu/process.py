#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for running subprocesses"""
from typing import Any, List, Mapping, Optional, Union
import dataclasses
import datetime
import logging
import subprocess


@dataclasses.dataclass
class ProcessRun:
    rc: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    time_seconds: Optional[float] = None
    hit_timeout: Optional[bool] = None


@dataclasses.dataclass
class ProcessSample:
    expected_rc: Optional[int] = None
    success: Optional[bool] = None
    attempts: Optional[int] = None
    timeout: Optional[bool] = None
    failed: List[ProcessRun] = dataclasses.field(default_factory=list)
    successful: ProcessRun = ProcessRun()


class LiveProcess:
    def __init__(self, cmd: Union[str, List[str]], timeout: Optional[int] = None, **kwargs):
        self.cmd: Union[str, List[str]] = cmd
        self.timeout: Optional[int] = timeout
        self.kwargs: Mapping[str, Any] = kwargs
        self.cleaned: bool = False

        # These set later on
        self.start_time: Optional[datetime.datetime] = None
        self.process: Optional[subprocess.Popen] = None
        self.end_time: Optional[datetime.datetime] = None
        self.attempt: Optional[ProcessRun] = None

    @staticmethod
    def _check_pipes(kwargs):
        if (
            not kwargs.get("stdout", False)
            and not kwargs.get("stderr", False)
            and not kwargs.get("capture_output", False)
        ):
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE

    def start(self):
        self._check_pipes(self.kwargs)
        self.start_time = datetime.datetime.utcnow()
        self.process = subprocess.Popen(self.cmd, **self.kwargs)

    def __enter__(self):
        self.start()
        return self

    def cleanup(self):
        if not self.cleaned:
            hit_timeout = False
            try:
                self.process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                hit_timeout = True
                self.process.kill()
                self.process.wait()

            self.end_time = datetime.datetime.utcnow()
            self.cleaned = True

            if self.process.stdout is not None:
                stdout = self.process.stdout.read()
            else:
                stdout = b""

            if self.process.stderr is not None:
                stderr = self.process.stderr.read()
            else:
                stderr = b""

            self.attempt = ProcessRun(
                stdout=stdout.strip().decode("utf-8"),
                stderr=stderr.strip().decode("utf-8"),
                rc=self.process.returncode,
                hit_timeout=hit_timeout,
                time_seconds=(self.end_time - self.start_time).total_seconds(),
            )

    def __exit__(self, *args, **kwargs):
        self.cleanup()


def sample_process(
    cmd: Union[str, List[str]],
    logger: logging.Logger,
    retries: int = 0,
    expected_rc: int = 0,
    timeout: Optional[int] = None,
    **kwargs,
) -> ProcessSample:
    """Run the given command as a subprocess within a shell"""

    logger.info(f"Running command with timeout of {timeout}: {cmd}")
    logger.debug(f"Using args: {kwargs}")

    result = ProcessSample(expected_rc=expected_rc)
    tries: int = 0

    while tries <= retries:
        tries += 1
        logger.debug(f"On try {tries}")

        with LiveProcess(cmd, timeout) as lp:
            lp.cleanup()
            attempt: ProcessRun = lp.attempt

        logger.info(f"Finished running. Got attempt: {attempt}")
        logger.debug(f"Got return code {attempt.rc}, expected {expected_rc}")
        if attempt.rc == expected_rc:
            logger.info(f"Command successful!")
            result.successful = attempt
            result.success = True
            break
        else:
            logger.warning(f"Got bad return code from command.")
            result.failed.append(attempt)
    else:
        # If we hit retry limit, we go here
        plural = "s" if tries > 1 else ""
        logger.critical(f"After {tries} attempt{plural}, unable to run command: {cmd}")
        result.success = False

    result.attempts = tries
    return result
