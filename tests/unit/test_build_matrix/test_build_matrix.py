#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test functionality of ci/build_matrix.py"""
import dataclasses
import importlib
import json
import string
import sys
from pathlib import Path

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


EXAMPLE_MATRIX_BUILDER_KWARGS_DICT = {
    "archs": ("arch1", "arch2"),
    "bones": ("bone1", "bone2"),
    "upstream_branch": "my_upstream_branch",
    "dockerfile_set": {"dockerfile1", "dockerfile2"},
    "changed_set": {"file1.py", "path/to/file2.py"},
}


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


def test_matrix_entry_new_parses_file_path_correctly():
    """Test that the new method of MatrixEntry class correctly parses file paths."""

    dockerfile = "my/path/to/benchmark/Dockerfile"
    changed = False
    archs = ["arch"]
    as_dict = {
        "dockerfile": dockerfile,
        "image_name": "benchmark",
        "benchmark": "benchmark",
        "env_var": "BENCHMARK_IMAGE",
        "archs": archs,
        "changed": changed,
    }
    entry = build_matrix.MatrixEntry.new(dockerfile=dockerfile, changed=changed, archs=archs)
    assert dataclasses.asdict(entry) == as_dict


def test_matrix_entry_as_json_correctly_creates_expected_json_dict():
    """Test that the as_json method of the MatrixEntry class correctly creates the expected JSON dicts."""

    dockerfile = "dockerfile"
    changed = True
    image_name = "bimage"
    benchmark = "benchmark"
    env_var = "BENCHMARK_IMAGE"
    entry = build_matrix.MatrixEntry(
        dockerfile=dockerfile,
        changed=changed,
        archs=["1", "2", "3"],
        image_name=image_name,
        benchmark=benchmark,
        env_var=env_var,
    )
    for index, json_dict in enumerate(entry.as_json()):
        arch = str(index + 1)
        assert json_dict["dockerfile"] == dockerfile
        assert json_dict["changed"] == changed
        assert json_dict["image_name"] == image_name
        assert json_dict["benchmark"] == benchmark
        assert json_dict["env_var"] == env_var
        assert json_dict["arch"] == arch
        assert json_dict["tag_prefix"] == f"{arch}-"
        json.dumps(json_dict)


def test_matrix_builder_can_instantiate_correctly():
    """Test that the MatrixBuilder instantiates correctly with given args and creates empty build matrix."""

    builder = build_matrix.MatrixBuilder(**EXAMPLE_MATRIX_BUILDER_KWARGS_DICT)
    assert builder.archs == EXAMPLE_MATRIX_BUILDER_KWARGS_DICT["archs"]
    assert builder.bones == EXAMPLE_MATRIX_BUILDER_KWARGS_DICT["bones"]
    assert builder.dockerfile_set == EXAMPLE_MATRIX_BUILDER_KWARGS_DICT["dockerfile_set"]
    assert builder.changed_set == EXAMPLE_MATRIX_BUILDER_KWARGS_DICT["changed_set"]
    assert builder.matrix == {"include": []}


def test_matrix_builder_reset_method_correctly_clears_matrix():
    """Test that the MatrixBuilder.reset method will correctly clear out the matrix."""

    builder = build_matrix.MatrixBuilder(**EXAMPLE_MATRIX_BUILDER_KWARGS_DICT)
    builder.matrix = "this is a matrix"
    builder.reset()
    assert isinstance(builder.matrix, dict)
    assert builder.matrix == {"include": []}


def test_matrix_builder_bones_changed_method_correctly_identifies_changed_bones():
    """Test that the MatrixBuilder.bones_changed method will identify if bones have changed."""

    builder = build_matrix.MatrixBuilder(**EXAMPLE_MATRIX_BUILDER_KWARGS_DICT)
    builder.bones = (r"b.*1", r"b.*2")
    builder.changed_set = {"bone1"}
    assert builder.bones_changed()
    builder.changed_set = {"bone2"}
    assert builder.bones_changed()
    builder.changed_set = {"bone3"}
    assert not builder.bones_changed()


def test_matrix_builder_benchmark_changed_method_correctly_identifies_if_benchmark_changed():
    """Test that the MatrixBuilder.benchmark_changed method will identify if a benchmark has changed."""

    changed = ["snafu/dns_perf_wrapper/Dockerfile", "snafu/benchmarks/uperf/Dockerfile", "uperf-wrapper"]
    not_changed = ["snafu/my_unchanged_benchmark/Dockerfile"]
    builder = build_matrix.MatrixBuilder(**EXAMPLE_MATRIX_BUILDER_KWARGS_DICT)
    builder.changed_set = build_matrix.parse_git_diff(EXAMPLE_GIT_DIFF)
    builder.dockerfile_set = build_matrix.parse_dockerfile_list(EXAMPLE_DF_LIST)

    for changed_benchmark in changed:
        assert builder.benchmark_changed(changed_benchmark)
    for not_changed_benchmark in not_changed:
        assert not builder.benchmark_changed(not_changed_benchmark)
