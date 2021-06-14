#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for running subprocesses"""
from typing import List, TypedDict, Tuple
import datetime
import logging
import subprocess


class ProcessRun(TypedDict, total=False):
    rc: int
    stdout: str
    stderr: str
    runtime: float


class ProcessSample(TypedDict, total=False):
    expected_rc: int
    success: bool
    attempts: int
    failed: List[ProcessRun]
    successful: ProcessRun


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
    result["failed"] = list()
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
            attempt["runtime"] = diff_seconds

        attempt["stdout"] = stdout
        attempt["stderr"] = stderr
        attempt["rc"] = rc
        logger.info(f"Finished running. Got attempt: {attempt}")

        logger.debug(f"Got return code {rc}, expected {expected_rc}")
        if rc == expected_rc:
            logger.info(f"Command successful!")
            result["successful"] = attempt
            result["success"] = True
            break
        else:
            logger.warning(f"Got bad return code from command.")
            result["failed"].append(attempt)
    else:
        # If we hit retry limit, we go here
        plural = "s" if tries > 1 else ""
        logger.critical(f"After {tries} attempt{plural}, unable to run command: {cmd}")
        result["success"] = False

    result["attempts"] = tries
    return result
