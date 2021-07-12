#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pytest conftest module for test configuration and fixtures."""
import os
import shlex
import subprocess

import pytest

COMPOSE_FILENAME = "docker-compose.yml"
COMPOSE_COMMAND = "podman-compose"


def pytest_addoption(parser):
    """Add options for default compose filename and default compose command."""

    parser.addoption(
        "--compose-filename",
        default=COMPOSE_FILENAME,
        help=f"Filename for compose files. Defaults to {COMPOSE_FILENAME}",
    )
    parser.addoption(
        "--compose-command",
        default=COMPOSE_COMMAND,
        help=f"Name of compose command. Defaults to {COMPOSE_COMMAND}",
    )


@pytest.fixture(scope="package")
def get_compose_file(request):
    """
    Determine the directory of invoked test and look for a compose file within.

    Returns
    -------
    tuple or None
        First item is the path to the directory that the test is located within. The second item
        is the path to the compose file, if one was found that is readable, otherwise ``None``.
    """

    package_directory = os.path.dirname(request.fspath)
    compose_file = os.path.join(package_directory, request.config.getoption("--compose-filename"))
    if os.access(compose_file, os.F_OK | os.R_OK):
        return package_directory, compose_file
    return package_directory, None


@pytest.fixture(scope="package")
def compose(request, get_compose_file):  # pylint: disable=W0621
    """
    Run the compose file found within test's package and cleanup after all tests in package finish.

    Raises
    ------
    RuntimeError
        If an error occurs while trying to start or stop docker-compose.

    Returns
    -------
    str
        Base docker-compose command that can be used by tests in order to exec into containers.
        For instance the string "docker-compose --file ... --project-directory ..." could be returned,
        which a test can then append " exec container_name echo 'hello world'" to, in order to run an echo
        command within the container with the name "container_name".
    """

    project_dir, compose_file = get_compose_file
    if compose_file is None:
        raise RuntimeError(
            f"Unable to find compose file within directory the test was collected from: {project_dir}"
        )

    compose_cmd = request.config.getoption("--compose-command")
    base_cmd = f"{compose_cmd} --file {compose_file} --project-directory {project_dir}"
    start_cmd = shlex.split(f"{base_cmd} up -d")
    try:
        subprocess.run(start_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as proc_error:
        raise RuntimeError(
            f"Unable to start compose file {compose_file}: {proc_error} Output: {proc_error.stdout}"
        ) from proc_error

    yield base_cmd

    end_cmd = shlex.split(f"{base_cmd} down --volumes")
    try:
        subprocess.run(end_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as proc_error:
        raise RuntimeError(
            f"Unable to stop compose file {compose_file}: {proc_error} Output: {proc_error.stdout}"
        ) from proc_error
