#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pytest conftest module for test configuration and fixtures."""
import datetime
import json
import os
import pathlib
import shlex
import subprocess
import time
from typing import List, Union

import pytest

MANIFEST_FILENAME = "deploy.yaml"


def pytest_addoption(parser):
    """Add options to pytest to control the manifest fixture."""

    parser.addoption(
        "--keep-pods", action="store_true", help="Don't clean deployed manifests after tests complete",
    )
    parser.addoption(
        "--use-existing-pods", action="store_true", help="Don't deploy manifests before tests start"
    )


def pytest_collection_modifyitems(config, items):
    """Modify functional tests by marking them with the benchmark name."""

    root_dir = pathlib.Path(config.rootdir)
    for item in items:
        # tests/functional/benchmark/...
        rel_path = pathlib.Path(item.fspath).relative_to(root_dir)
        test_type = rel_path.parts[1]
        if test_type == "functional":
            benchmark_name = rel_path.parts[2]
            # need to add custom marker, otherwise will get a warning
            config.addinivalue_line("markers", benchmark_name)
            mark = getattr(pytest.mark, benchmark_name)
            item.add_marker(mark)


def sub_env_in_file(file_path: str) -> str:
    """
    Given path to a file, return contents of the file with environment variable substitution performed.

    If running these manifests manually, please feel free to use the ``envsubst`` command. This functional
    is only implementend because it is compatible on images that may not have such a helpful command
    available.

    Parameters
    ----------
    file_path : str
        Path to the file to substitute environment variables in

    Returns
    -------
    str
        Contents of the file with environment variables substituted for their values.

    Raises
    ------
    CalledProcessError
    """

    sub_cmd = f'eval "echo \\"$(cat {file_path})\\""'
    proc = subprocess.run(sub_cmd, stdout=subprocess.PIPE, shell=True, check=True, env=os.environ)
    return proc.stdout.decode("utf-8")


@pytest.fixture(scope="package")
def get_manifest(request):
    """
    Determine the directory of invoked test and look for a manifest file within.

    Returns
    -------
    tuple or None
        First item is the path to the directory that the test is located within. The second item
        is the path to the manifest file, if one was found that is readable, otherwise ``None``. The
        third item is the content of the manifest file with environment variable substitution perfomed.
    """

    package_directory = os.path.dirname(request.fspath)
    manifest_file = os.path.join(package_directory, MANIFEST_FILENAME)
    if os.access(manifest_file, os.F_OK | os.R_OK):
        return package_directory, manifest_file, sub_env_in_file(manifest_file)
    return package_directory, None, None


@pytest.fixture(scope="package")
def manifest(request, get_manifest):  # pylint: disable=W0621
    """
    Start the manifest file found within test's package and cleanup after all tests in package finish.

    Expected format for the manifest file is a kubernetes definition that creates a pod or deployment.
    Will manage using ``podman play kube``. Expects pods created to be labeled with "test=snafu".
    If the label doesn't exist, then cleanup will not occur.

    In order to pass config files from the host into containers, one option is to use a hostPath volume
    mount. Note that this option requires the configuration files and/or directory to be labeled with the
    type ``container_file_t`` or ``container_ro_file_t``, otherwise the container will not have permission
    to use the mounted files. See https://www.mankier.com/8/container_selinux for more info.

    Another method is to disable SELinux within the container which is mounting the config files. See
    https://github.com/containers/podman/pull/5307#issuecomment-590830455 for more information.

    Raises
    ------
    RuntimeError
        If an error occurs while trying to start or stop the manifest

    Returns
    -------
    str
    """

    project_dir, manifest_file, manifest_content = get_manifest
    if manifest_file is None:
        raise RuntimeError(
            f"Unable to find manifest file within directory the test was collected from: {project_dir}"
        )

    exec_prefix = "podman exec {container}"
    try:
        if not request.config.getoption("--use-existing-pods"):
            start_cmd = f'echo "{manifest_content}" | podman play kube -'
            proc = subprocess.run(
                start_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, shell=True
            )
            print(proc.stdout)
        yield exec_prefix
    except subprocess.CalledProcessError as proc_error:
        raise RuntimeError(
            f"Unable to create manifest file {manifest_file}: {proc_error} Output: {proc_error.stdout}"
        ) from proc_error
    finally:
        if not request.config.getoption("--keep-pods"):
            end_cmd = 'podman pod ps --format "{{.ID}}" --filter label=test=snafu | xargs podman pod rm -f'
            try:
                subprocess.run(
                    end_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, shell=True
                )
            except subprocess.CalledProcessError as proc_error:
                raise RuntimeError(
                    f"Unable to cleanup manifest file {manifest_file}: {proc_error} Output: "
                    f"{proc_error.stdout}"
                ) from proc_error


@pytest.fixture
def command_poll():
    """
    Return function which polls the given command until success.

    Below is information for the returned function:

    Arguments
    ---------
    command : str or list of str
        Command to execute and wait for success on
    timeout : int
        Number of total seconds to wait before giving up
    wait : int
        Number of seconds to wait inbetween attempts
    shell : bool, optional
        If True, will run command inside shell (i.e. set the shell option to true in subprocess.run).
        Defaults to False

    Returns
    -------
    str or None
        stdout and stderr of successful command, otherwise None
    """

    def _command_poll(
        command: Union[str, List[str]], timeout: int, wait: int, shell: bool = False
    ) -> Union[str, None]:
        """Execute given command until success or timeout is hit."""

        start = datetime.datetime.now()
        success = False
        while (datetime.datetime.now() - start).total_seconds() < timeout:
            try:
                proc = subprocess.run(
                    command, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True
                )
                success = True
                break
            except subprocess.CalledProcessError:
                time.sleep(wait)

        if success:
            return proc.stdout.decode("utf-8")
        return None

    return _command_poll


@pytest.fixture
def wait_for_es(command_poll):  # pylint: disable=W0621
    """
    Return function that waits for elasticsearch instance to be up and running within a container.

    Assumes that the container has curl available. Will wait for cluster to be in the given status or any
    status healthier than the given status.

    Below is information for returned function:

    Arguments
    ---------
    exec_prefix : str
        Prefix that our health check command will be appendend to. Should be used in order to have
        a container execute the health check. For instance: "podman exec benchmark-test-pod-client"
    es_url : str
        URL to ES endpoint
    timeout : int
        Timeout value to pass to the heath-check query (seconds)
    wait : int
        Time inbetween queries to health check (seconds)
    status : str
        Status to wait for ES to be in. Must be one of "green", "yellow", "red".

    Returns
    -------
    bool
        True if ES is available within given timeout, otherwise False
    """

    def _wait_for_es(exec_prefix: str, es_url: str, timeout: int, wait: int, status: str) -> bool:
        status_values = ("red", "yellow", "green")
        if status not in status_values:
            raise ValueError(f"Expected green, yellow or red for status, got: {status}")
        status_index = status_values.index(status)
        accepted_status_values = status_values[status_index:]

        if not es_url.endswith("/"):
            es_url += "/"
        api_url = f"{es_url}_cluster/health?wait_for_status={status}&timeout={timeout}s"
        command = shlex.split(f"{exec_prefix} curl -s {api_url}")
        result_stdout = command_poll(command, timeout, wait)

        if result_stdout is not None:
            result_json = json.loads(result_stdout)
            return result_json["status"] in accepted_status_values
        return False

    return _wait_for_es
