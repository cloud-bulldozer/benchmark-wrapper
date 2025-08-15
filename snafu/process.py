#!/usr/bin/env python3
"""Tools for running subprocesses."""
import dataclasses
import datetime
import logging
import subprocess
from collections.abc import Iterable


@dataclasses.dataclass
class ProcessRun:
    """Represent a single run of a subprocess without retries."""

    rc: int | None = None  # pylint: disable=C0103
    stdout: str | None = None
    stderr: str | None = None
    time_seconds: float | None = None
    hit_timeout: bool | None = None


@dataclasses.dataclass
class ProcessSample:
    """Represent a process that will be retried on failure."""

    expected_rc: int | None = None
    success: bool | None = None
    attempts: int | None = None
    timeout: int | None = None
    failed: list[ProcessRun] = dataclasses.field(default_factory=list)
    successful: ProcessRun | None = None


def get_process_sample(
    cmd: str | list[str],
    logger: logging.Logger,
    retries: int = 0,
    expected_rc: int = 0,
    timeout: int | None = None,
    **kwargs,
) -> ProcessSample:
    """
    Run the given command as a subprocess, retrying if the command fails.

    Essentially just a wrapper around :py:func:`subprocess.run` that will retry running a subprocess if
    it fails, returning a :py:class:`~snafu.process.ProcessSample` detailing the results.

    This function expects a logger because it is expected that it will be used by benchmarks, which should
    be logging their progress anyways.

    Parameters
    ----------
    cmd : str or list of str
        Command to run. Can be string or list of strings if using :py:mod:`shlex`
    logger : logging.Logger
        Logger to use in order to log progress.
    retries : int, optional
        Number of retries to perform. Defaults to zero, which means that the function will run the process
        once, not retrying on failure.
    expected_rc : int, optional
        Expected return code of the process. Will be used to determine if the process ran successfully or not.
    timeout : int, optional
        Time in seconds to wait for process to complete before killing it.
    kwargs
        Extra kwargs will be passed to :py:class:`~snafu.process.LiveProcess`

    Returns
    -------
    ProcessSample
    """

    logger.debug(f"Running command: {cmd}")
    logger.debug(f"Using args: {kwargs}")

    result = ProcessSample(expected_rc=expected_rc, timeout=timeout)
    tries: int = 0
    tries_plural: str = ""

    if (
        kwargs.get("capture_output", False)
        or {"stdout", "stderr", "capture_output"}.intersection(set(kwargs)) == set()
    ):
        kwargs["capture_output"] = True

    while tries <= retries:
        tries += 1
        logger.debug(f"On try {tries}")

        attempt = ProcessRun()
        start_time = datetime.datetime.now(datetime.UTC)
        try:
            proc = subprocess.run(cmd, check=False, timeout=timeout, **kwargs)
        except subprocess.TimeoutExpired as timeout_error:
            attempt.hit_timeout = True
            attempt.time_seconds = timeout_error.timeout
            stdout = timeout_error.stdout
            stderr = timeout_error.stderr
        else:
            attempt.time_seconds = (datetime.datetime.now(datetime.UTC) - start_time).total_seconds()
            attempt.hit_timeout = False
            attempt.rc = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr

        if stdout is not None:
            attempt.stdout = stdout.decode("utf-8")
        if stderr is not None:
            attempt.stderr = stderr.decode("utf-8")

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


def sample_process(  # pylint: disable=too-many-positional-arguments
    cmd: str | list[str],
    logger: logging.Logger,
    retries: int = 0,
    expected_rc: int = 0,
    timeout: int | None = None,
    num_samples: int = 1,
    **kwargs,
) -> Iterable[ProcessSample]:
    """Yield multiple samples of the given command."""

    _plural = "s" if num_samples > 1 else ""
    logger.info(f"Collecting {num_samples} sample{_plural} of command {cmd}")
    for sample_num in range(1, num_samples + 1):
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
