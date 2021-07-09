#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pytest conftest module for test configuration and fixtures."""
import os
import shlex
import subprocess

import pytest

COMPOSE_FILENAME = "docker-compose.yml"


@pytest.fixture(scope="package")
def get_compose_file(request):
    """
    Determine the directory of invoked test and look for a compose file within.

    Returns
    -------
    tuple or None
        First item is the path to the directory that the compose file was found in, second
        is the path to the compose file. If a compose file was not found, then ``None`` is returned.
    """

    package_directory = os.path.dirname(request.fspath)
    compose_file = os.path.join(package_directory, COMPOSE_FILENAME)
    if os.access(compose_file, os.F_OK | os.R_OK):
        return package_directory, compose_file
    return None


@pytest.fixture(scope="package")
def compose(get_compose_file):  # pylint: disable=W0621
    """
    Run the compose file found within test's package and cleanup after all tests in package finish.

    Returns
    -------
    None
    """

    project_dir, compose_file = get_compose_file
    if get_compose_file is None:
        return

    base_cmd = f"docker-compose --file {compose_file} --project-directory {project_dir}"
    start_cmd = shlex.split(f"{base_cmd} up")
    try:
        subprocess.run(start_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as proc_error:
        raise RuntimeError(
            f"Unable to start compose file {compose_file}: {proc_error} Output: {proc_error.stdout}"
        ) from proc_error

    yield

    end_cmd = shlex.split(f"{base_cmd} down --volumes")
    try:
        subprocess.run(end_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as proc_error:
        raise RuntimeError(
            f"Unable to stop compose file {compose_file}: {proc_error} Output: {proc_error.stdout}"
        ) from proc_error
