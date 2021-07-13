#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pytest conftest module for test configuration and fixtures."""
import os
import pathlib
import subprocess

import pytest

MANIFEST_FILENAME = "deploy.yaml"


def pytest_collection_modifyitems(config, items):
    """Modify functional tests by marking them with the benchmark name."""

    root_dir = pathlib.Path(config.rootdir)
    for item in items:
        # tests/functional/benchmark/...
        rel_path = pathlib.Path(item.fspath).relative_to(root_dir)
        test_type = rel_path.parts[1]
        benchmark_name = rel_path.parts[2]
        if test_type == "functional":
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
def manifest(get_manifest):  # pylint: disable=W0621
    """
    Start the manifest file found within test's package and cleanup after all tests in package finish.

    Expected format for the manifest file is a kubernetes definition that creates a pod or deployment.
    Will manage using ``podman play kube``. Expects pods created to be labeled with "test=snafu".
    If the label doesn't exist, then cleanup will not occur.

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

    start_cmd = f'echo "{manifest_content}" | podman play kube -'
    try:
        proc = subprocess.run(
            start_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, shell=True
        )
        print(proc.stdout)
        yield "podman exec {container}"
    except subprocess.CalledProcessError as proc_error:
        raise RuntimeError(
            f"Unable to create manifest file {manifest_file}: {proc_error} Output: {proc_error.stdout}"
        ) from proc_error
    finally:
        end_cmd = 'podman pod ps --format "{{.ID}}" --filter label=test=snafu | xargs podman pod rm -f'
        try:
            subprocess.run(end_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, shell=True)
        except subprocess.CalledProcessError as proc_error:
            raise RuntimeError(
                f"Unable to cleanup manifest file {manifest_file}: {proc_error} Output: {proc_error.stdout}"
            ) from proc_error
