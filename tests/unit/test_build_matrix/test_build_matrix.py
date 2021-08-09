#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test functionality of ci/build_matrix.py"""
import string
import sys
from pathlib import Path
import importlib


# Load the build_matrix.py file using importlib.
# See https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly for reference.
_bm_source_path = Path(__file__).parent.parent.parent.parent.joinpath("ci", "build_matrix.py").resolve()
_bm_spec = importlib.util.spec_from_file_location("build_matrix", _bm_source_path)
build_matrix = importlib.util.module_from_spec(_bm_spec)
sys.modules["build_matrix"] = build_matrix
_bm_spec.loader.exec_module(build_matrix)


with open(Path(__file__).parent.joinpath("git_diff_test.txt")) as git_diff_test:
    EXAMPLE_GIT_DIFF = git_diff_test.read()

with open(Path(__file__).parent.joinpath("find_df_test.txt")) as find_df_test:
    EXAMPLE_DF_LIST = find_df_test.read()


def test_parse_git_diff_returns_set_with_right_number_of_files():
    """Test that the parse_git_diff function properly parses given git-diff output."""

    result = build_matrix.parse_git_diff(EXAMPLE_GIT_DIFF)
    assert isinstance(result, set)
    assert len(result) == len(EXAMPLE_GIT_DIFF.strip().split("\n"))
    for file_path in result:
        assert all(char not in string.whitespace for char in file_path)


def test_parse_dockerfile_list_returns_set_with_right_number_of_files(monkeypatch):
    """Test that the parse_dockerfile_list function properly parses given output."""

    # Reset ignores for now
    monkeypatch.setattr(build_matrix, "IGNORES", tuple())
    result = build_matrix.parse_dockerfile_list(EXAMPLE_DF_LIST)
    assert isinstance(result, set)
    assert len(result) == len(EXAMPLE_DF_LIST.strip().split("\n"))
    for file_path in result:
        assert all(char not in string.whitespace for char in file_path)


def test_parse_dockerfile_list_returns_set_with_files_ignored(monkeypatch):
    """Test that the parse_dockerfile_list function properly ignores target dockerfiles."""

    monkeypatch.setattr(build_matrix, "IGNORES", (r"Dockerfile\.ppc64le$",))

    result = build_matrix.parse_dockerfile_list(EXAMPLE_DF_LIST)
    # The test file has 8 ppc64le dockerfiles
    assert len(result) == len(EXAMPLE_DF_LIST.strip().split("\n")) - 8
