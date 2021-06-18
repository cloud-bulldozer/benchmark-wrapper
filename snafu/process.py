#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for running subprocesses"""
from typing import List, Optional, Tuple
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


@dataclasses.dataclass
class ProcessSample:
    expected_rc: Optional[int] = None
    success: Optional[bool] = None
    attempts: Optional[int] = None
    failed: List[ProcessRun] = list()
    successful: ProcessRun = ProcessRun()


# TODO: environment variables
# TODO: Allow for specifying shell=False
# TODO: Confirm process exits before returning
# TODO: Add more robust proccess running that allows benchmarks to pull stdout/stderr in real time and log


def _run_process(cmd: str) -> Tuple[str, str, int]:
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.strip().decode("utf-8"), stderr.strip().decode("utf-8"), process.returncode


def sample_process(
    cmd: str, logger: logging.Logger, retries: int = 0, time: bool = False, expected_rc: int = 0
) -> ProcessSample:
    """Run the given command as a subprocess within a shell"""

    logger.info(f"Running command: {cmd}")
    result = ProcessSample(expected_rc=expected_rc)
    tries: int = 0

    while tries <= retries:
        tries += 1
        logger.debug(f"On try {tries}")
        attempt = ProcessRun()

        if time:
            start_time = datetime.datetime.utcnow()

        stdout, stderr, rc = _run_process(cmd)

        if time:
            end_time = datetime.datetime.utcnow()
            diff_seconds = (end_time - start_time).total_seconds()
            attempt.time_seconds = diff_seconds

        attempt.stdout = stdout
        attempt.stderr = stderr
        attempt.rc = rc
        logger.info(f"Finished running. Got attempt: {attempt}")

        logger.debug(f"Got return code {rc}, expected {expected_rc}")
        if rc == expected_rc:
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
