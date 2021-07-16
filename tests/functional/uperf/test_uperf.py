#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Perform functional tests of uperf."""
import json
import shlex
import subprocess

POD = "uperf-test-pod"  # pod prefix where containers are placed
ES = "es01"  # container name for elasticsearch
CLIENT = "uperf"  # container name for uperf client
TIMEOUT = 60  # universal timeout value we can use while waiting for containers to be ready


def test_uperf_is_available(manifest):
    """
    Test that we can run a command within the 'uperf' container.

    If this test fails then either the manifest file has changed or something went wrong starting
    the container.
    """

    result = subprocess.run(
        shlex.split(f"{manifest.format(container=f'{POD}-{CLIENT}')} echo 'Hello World'"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    result_stdout = result.stdout.decode("utf-8")
    assert "Hello World" in result_stdout


def test_es_is_available(manifest, command_poll):
    """
    Test that the elasticsearch instance is up and running.

    If this test fails then either the manifest file has changed or something went wrong starting
    the container.
    """

    api_url = f"http://localhost:9200/_cluster/health?wait_for_status=green&timeout={TIMEOUT}s"
    command = shlex.split(f"{manifest.format(container=f'{POD}-{CLIENT}')} curl -s {api_url}")
    result_stdout = command_poll(command, TIMEOUT, 1)
    assert result_stdout is not None
    result_json = json.loads(result_stdout)
    assert result_json["status"] == "green"
