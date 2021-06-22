#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for running subprocesses"""
from typing import Any, List, Mapping, Optional, Union
import dataclasses
import datetime
import logging
import subprocess
import threading
import queue


@dataclasses.dataclass
class ProcessRun:
    rc: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    time_seconds: Optional[float] = None


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
        self.stdout: queue.Queue = queue.Queue()
        self.stderr: queue.Queue = queue.Queue()
        self._stdout: bytes = b""
        self._stderr: bytes = b""
        self.attempt: Optional[ProcessRun] = ProcessRun()

        # These set later on
        self.start_time: Optional[datetime.datetime] = None
        self.process: Optional[subprocess.Popen] = None
        self.end_time: Optional[datetime.datetime] = None
        self.threads: Optional[List[threading.Thread]] = None

    @staticmethod
    def _check_pipes(kwargs):
        if (
            not kwargs.get("stdout", False)
            and not kwargs.get("stderr", False)
            and not kwargs.get("capture_output", False)
        ):
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE

    def _enqueue_line_from_fh(self, fh, queue, store):
        for line in iter(fh.readline, b""):
            queue.put(line)
            # use this method since running in separate thread
            setattr(self, store, getattr(self, store) + line)

    def start(self):
        self._check_pipes(self.kwargs)
        self.start_time = datetime.datetime.utcnow()
        self.process = subprocess.Popen(self.cmd, **self.kwargs)
        self.threads = [
            threading.Thread(
                target=self._enqueue_line_from_fh,
                args=(self.process.stdout, self.stdout, "_stdout"),
                daemon=True,
            ),
            threading.Thread(
                target=self._enqueue_line_from_fh,
                args=(self.process.stderr, self.stderr, "_stderr"),
                daemon=True,
            ),
        ]

        [t.start() for t in self.threads]

    def __enter__(self):
        self.start()
        return self

    def cleanup(self):
        if not self.cleaned:
            if self.timeout is not None:
                try:
                    self.process.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            else:
                self.process.wait()

            self.end_time = datetime.datetime.utcnow()
            [t.join() for t in self.threads]

            self.cleaned = True
            self.attempt.stdout = self._stdout.decode("utf-8")
            self.attempt.stderr = self._stderr.decode("utf-8")
            self.attempt.rc = self.process.returncode
            self.attempt.time_seconds = (self.end_time - self.start_time).total_seconds()

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

    logger.debug(f"Running command with timeout of {timeout}: {cmd}")
    logger.debug(f"Using args: {kwargs}")

    result = ProcessSample(expected_rc=expected_rc)
    tries: int = 0
    tries_plural: str = ""

    while tries <= retries:
        tries += 1
        logger.debug(f"On try {tries}")

        with LiveProcess(cmd, timeout) as lp:
            lp.cleanup()
            attempt: ProcessRun = lp.attempt

        logger.debug(f"Finished running. Got attempt: {attempt}")
        logger.debug(f"Got return code {attempt.rc}, expected {expected_rc}")
        if attempt.rc == expected_rc:
            logger.debug(f"Command finished with {tries} attempt{tries_plural}: {cmd}")
            result.successful = attempt
            result.success = True
            break
        else:
            logger.warning(f"Got bad return code from command: {cmd}.")
            result.failed.append(attempt)

        tries_plural = "s"
    else:
        # If we hit retry limit, we go here
        logger.critical(f"After {tries} attempt{tries_plural}, unable to run command: {cmd}")
        result.success = False

    result.attempts = tries
    return result
