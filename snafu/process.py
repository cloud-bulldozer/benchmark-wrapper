#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for running subprocesses."""
import dataclasses
import datetime
import logging
import queue
import subprocess
import threading
from typing import Any, Iterable, List, Mapping, Optional, Union


@dataclasses.dataclass
class ProcessRun:
    """Represent a single run of a subprocess without retries."""

    rc: Optional[int] = None  # pylint: disable=C0103
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    time_seconds: Optional[float] = None


@dataclasses.dataclass
class ProcessSample:
    """Represent a process that will be retried on failure."""

    expected_rc: Optional[int] = None
    success: Optional[bool] = None
    attempts: Optional[int] = None
    timeout: Optional[bool] = None
    failed: List[ProcessRun] = dataclasses.field(default_factory=list)
    successful: ProcessRun = ProcessRun()


class LiveProcess:
    r"""
    Open a subprocess and get live access to stdout and stderr.

    Context manager that runs the given command on entry, cleans up on exit, and creates
    a ProcessRun object summarizing the results. The process's stdout and stderr will be captured and
    exposed via the ``stdout`` and ``stderr`` :py:class:`queue.Queue` attributes.

    By default a pipe for stdout and stderr are created and given to the created subprocess. If ``stdout``,
    ``stderr`` or ``capture_output`` options are given by the user through kwargs, then no automatic pipe
    creation will be performed.

    Parameters
    ----------
    cmd : str or list of str
        Command to run. Can be string or list or string if using :py:mod:`shlex`
    timeout : int, optional
        When cleaning up the running process, this value specifies time in seconds to wait for
        process to finish before killing it.
    **kwargs
        Additional kwargs given will be passed directly to the :py:class:`subprocess.Popen` call used in the
        background to launch the command.

    Attributes
    ----------
    cmd : str or list of str
        Command to execute
    timeout : int or None
        Timeout value in seconds, if given
    kwargs : mapping
        kwargs to pass to :py:class:subprocess.Popen`
    attempt : ProcessRun
        ProcessRun instance describing the run process
    process : subprocess.Popen
        Popen object created for the run command
    start_time : datetime.datetime
        Datetime object representing approximate time that the process was started
    end_time : datetime.datetime
        Datetime object representing approximate time that the process exited

    Examples
    --------
    >>> from snafu.process import LiveProcess
    >>> with LiveProcess("echo 'test'; sleep 0.5; echo 'test2'", shell=True) as lp:
    ...     print(lp.stdout.get())
    ...     print(lp.stdout.get())  # will block until another line is ready
    ...     run = lp.attempt
    ...
    b'test\n'
    b'test2\n'
    >>> run.stdout  # decoded for us
    'test\ntest2\n'
    """

    def __init__(self, cmd: Union[str, List[str]], timeout: Optional[int] = None, **kwargs):
        """Create instance attributes with None for defaults as needed and check pipe arguments in kwargs."""
        self.cmd: Union[str, List[str]] = cmd
        self.timeout: Optional[int] = timeout
        self.kwargs: Mapping[str, Any] = kwargs
        self.stdout: queue.Queue = queue.Queue()
        self.stderr: queue.Queue = queue.Queue()
        self.attempt: Optional[ProcessRun] = ProcessRun()
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[datetime.datetime] = None
        self.end_time: Optional[datetime.datetime] = None

        self._cleaned: bool = False
        self._stdout: bytes = b""
        self._stderr: bytes = b""
        self._threads: Optional[List[threading.Thread]] = None

        self._check_pipes(self.kwargs)

    @staticmethod
    def _check_pipes(kwargs):
        if (
            not kwargs.get("stdout", False)
            and not kwargs.get("stderr", False)
            and not kwargs.get("capture_output", False)
        ):
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE

    def _enqueue_line_from_fh(self, file_handler, queue_attr, store):
        if file_handler is not None:
            for line in iter(file_handler.readline, b""):
                queue_attr.put(line)
                # use this method since running in separate thread
                setattr(self, store, getattr(self, store) + line)

    def start(self):
        """Start the subprocess and create threads for capturing output."""

        self.start_time = datetime.datetime.utcnow()
        self.process = subprocess.Popen(self.cmd, **self.kwargs)  # pylint: disable=R1732
        self._threads = [
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

        for thread in self._threads:
            thread.start()

    def __enter__(self):
        """Call start method and return self."""
        self.start()
        return self

    def cleanup(self):
        """Cleanup the subprocess with a timeout and populate the ProcessRun instance at ``attempt``."""
        if not self._cleaned:
            if self.timeout is not None:
                try:
                    self.process.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            else:
                self.process.wait()

            self.end_time = datetime.datetime.utcnow()
            for thread in self._threads:
                thread.join()

            self._cleaned = True
            self.attempt.stdout = self._stdout.decode("utf-8")
            self.attempt.stderr = self._stderr.decode("utf-8")
            self.attempt.rc = self.process.returncode
            self.attempt.time_seconds = (self.end_time - self.start_time).total_seconds()

    def __exit__(self, *args, **kwargs):
        """Call cleanup method on exit of context."""
        self.cleanup()


def get_process_sample(
    cmd: Union[str, List[str]],
    logger: logging.Logger,
    retries: int = 0,
    expected_rc: int = 0,
    timeout: Optional[int] = None,
    **kwargs,
) -> ProcessSample:
    """Run the given command as a subprocess."""

    logger.debug(f"Running command with timeout of {timeout}: {cmd}")
    logger.debug(f"Using args: {kwargs}")

    result = ProcessSample(expected_rc=expected_rc)
    tries: int = 0
    tries_plural: str = ""

    while tries <= retries:
        tries += 1
        logger.debug(f"On try {tries}")

        with LiveProcess(cmd, timeout, **kwargs) as proc:
            proc.cleanup()
            attempt: ProcessRun = proc.attempt

        logger.debug(f"Finished running. Got attempt: {attempt}")
        logger.debug(f"Got return code {attempt.rc}, expected {expected_rc}")
        if attempt.rc != expected_rc:
            logger.warning(f"Got bad return code from command: {cmd}.")
            result.failed.append(attempt)
        else:
            logger.debug(f"Command finished with {tries} attempt{tries_plural}: {cmd}")
            result.successful = attempt
            result.success = True
            break
        tries_plural = "s"
    else:
        # If we hit retry limit, we go here
        logger.critical(f"After {tries} attempt{tries_plural}, unable to run command: {cmd}")
        result.success = False

    result.attempts = tries
    return result


def sample_process(
    cmd: Union[str, List[str]],
    logger: logging.Logger,
    retries: int = 0,
    expected_rc: int = 0,
    timeout: Optional[int] = None,
    num_samples: int = 1,
    **kwargs,
) -> Iterable[ProcessSample]:
    """Yield multiple samples of the given command."""

    _plural = "s" if num_samples > 1 else ""
    logger.info(f"Collecting {num_samples} sample{_plural} of command {cmd}")
    for sample_num in range(1, num_samples):
        logger.debug(f"Starting sample {sample_num}")
        sample: ProcessSample = get_process_sample(
            cmd, logger, retries=retries, expected_rc=expected_rc, timeout=timeout, **kwargs
        )
        logger.debug(f"Got sample for command {cmd}: {sample}")

        if not sample.success:
            logger.warning(f"Sample {sample_num} has failed state for command {cmd}")
        else:
            logger.debug(f"Sample {sample_num} has success state for command {cmd}")

        yield sample
        logger.debug(f"Collected sample {sample_num} for command {cmd}")

    logger.info(f"Finished collecting {num_samples} sample{_plural} for command {cmd}")
