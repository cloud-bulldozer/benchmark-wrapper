#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Perform functional tests of uperf."""
import json
import shlex
import subprocess
import uuid

POD = "uperf-test-pod"  # pod prefix where containers are placed
ES = "es01"  # container name for elasticsearch
CLIENT = "uperf"  # container name for uperf client
SERVER = "uperf_server"  # container name for uperf server
TIMEOUT = 60  # universal timeout value we can use while waiting for containers or commands
WAIT = 2  # universal time inbetween attempts we can use while waiting for containers or commands


def test_uperf_is_available(manifest):
    """
    Test that we can run a command within the 'uperf' and 'uperf_server' container.

    If this test fails then either the manifest file has changed or something went wrong starting
    the container.
    """

    for container in (CLIENT, SERVER):
        result = subprocess.run(
            shlex.split(f"{manifest.format(container=f'{POD}-{container}')} echo 'Hello World'"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        result_stdout = result.stdout.decode("utf-8")
        assert "Hello World" in result_stdout


def test_es_is_available(manifest, wait_for_es):
    """
    Test that the elasticsearch instance is up and running.

    If this test fails then either the manifest file has changed or something went wrong starting
    the container.
    """

    assert wait_for_es(
        f"{manifest.format(container=f'{POD}-{CLIENT}')}", "http://localhost:9200", TIMEOUT, WAIT, "green"
    )


def _run_uperf(manifest: str, wait_for_es, config: str) -> None:
    """
    Run uperf with the given config and assert success.

    Will wait for es to at least be in yellow status.

    Parameters
    ----------
    manifest : str
        manifest fixture
    wait_for_es
        wait_for_es fixture
    config : str
        Full path to config file within uperf client container

    Raises
    ------
    AssertionError
        If results were not found within elasticsearch
    subprocess.CalledProcessError
        If error occured within run_snafu or within curl

    Returns
    -------
    None
    """

    exec_prefix = manifest.format(container=f"{POD}-{CLIENT}")

    assert wait_for_es(exec_prefix, "http://localhost:9200", TIMEOUT, WAIT, "yellow",)

    run_id = str(uuid.uuid4())
    print(f"Using run_id: {run_id}")  # it is ugly, but pytest captures stdout for debug

    run_snafu_command = f"run_snafu --tool uperf --config {config} --run-id={run_id} --verbose"
    command = shlex.split(f"{exec_prefix} {run_snafu_command}")
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True,)
    print(proc.stdout.decode("utf-8"))

    # Need to refresh so our documents are ready to be searched
    subprocess.run(shlex.split(f"{exec_prefix} curl -s -X GET http://localhost:9200/_refresh"), check=True)

    # Since we don't create an index template, it's important to use the "match" query
    # rather than the "term" query
    # See: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-term-query.html
    json_query = json.dumps({"query": {"match": {"run_id": f"{run_id}"}}})
    query_command = (
        "curl -s -X GET http://localhost:9200/_search -H 'Content-Type: application/json' -d "
        f"'{json_query}'"
    )
    command = shlex.split(f"{exec_prefix} {query_command}")
    query_proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    es_query_stdout = query_proc.stdout.decode("utf-8")
    print(f"Query results: {es_query_stdout}")
    es_query_result = json.loads(es_query_stdout)

    assert es_query_result["timed_out"] is False
    assert es_query_result["_shards"]["total"] == es_query_result["_shards"]["successful"]
    assert es_query_result["hits"]["total"]["value"] > 0


def test_run_uperf_bidirec_workload(manifest, wait_for_es):
    """
    Test running the Uperf bidirec benchmark with run_snafu.

    Will use profile and config found within ``/root/configs/bidirec``. These files are included into
    the uperf client container within the deploy manifest. Will check for results in elasticsearch in
    order to verify test was successful.
    """

    _run_uperf(manifest, wait_for_es, "/root/configs/bidirec/config.yaml")


def test_run_uperf_rr_workload(manifest, wait_for_es):
    """
    Test running the Uperf rr benchmark with run_snafu.

    Will use profile and config found within ``/root/configs/rr``. These files are included into
    the uperf client container within the deploy manifest. Will check for results in elasticsearch in
    order to verify test was successful.
    """

    _run_uperf(manifest, wait_for_es, "/root/configs/rr/config.yaml")


def test_run_uperf_stream_workload(manifest, wait_for_es):
    """
    Test running the Uperf stream benchmark with run_snafu.

    Will use profile and config found within ``/root/configs/stream``. These files are included into
    the uperf client container within the deploy manifest. Will check for results in elasticsearch in
    order to verify test was successful.
    """

    _run_uperf(manifest, wait_for_es, "/root/configs/stream/config.yaml")
