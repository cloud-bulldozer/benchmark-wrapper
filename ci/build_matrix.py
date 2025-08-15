#!/usr/bin/env python3
"""
Create Github Actions Job Matrix for building dockerfiles.

Expects one optional input as the first positional argument. This is the upstream branch name, which
the current working tree will be compared against in order to understand if a benchmark should
be labeled as changed or not. If this input is not given, then "master" will be used.

A benchmark will be labeled as changed if any of the following conditions are met:

  * A core component of benchmark-wrapper has changed, known as a 'bone'. Please see $bones for a list of
    regex searches.
  * Any of the files underneath the benchmark's module path

The JSON output looks like this, in accordance to the GHA Job Matrix Format:

```json
{
    "include": [
        {
            "dockerfile": "path to dockerfile relative to repo root",
            "image_name": "name of the image (i.e. name of directory containing the DF)",
            "benchmark": "name of the benchmark (i.e. name of directory containing the DF)",
            "env_var": "environment variable where image URL will be stored (i.e. <BENCHMARK>_IMAGE)",
            "tag_suffix": "suffix of the image tag that should be used (i.e. arch of the DF with a dash)",
            "tags": "space separated list of tags that should be applied to the image",
            "arch": "architecture that the DF should be built on",
            "changed": "whether or not changes have been made which require the benchmark to be tested",
        },
        ...
    ]
}
```

If the `--manifest` option is given, then GHA job matrices will be printed which can be used for
building and pushing multi-arch image manifests to quay. The output looks like this:

```json
{
    "build": "build matrix from above",
    "manifest": {
        "include": [
            {
                "benchmark": "name of the benchmark associated with the image",
                "image_name": "name of the image",
                "dockerfile": "relative path to dockerfile of image",
                "tag": "tag the manifest will be built for",
                "archs": "archictectures that should be added into the image manifest, space separated",
                "tag_suffixes": "tag suffixes to add into the image manifest, space separated",
                "changed": "whether or not changes have been made which require the benchmark to be tested",
            },
            ...
        ]
    }
}
"""
import argparse
import dataclasses
import json
import pathlib
import re
import shlex
import subprocess
from collections.abc import Iterable

ARCHS = (
    "amd64",
    "arm64",
)
BONES = (
    r"ci/",
    r".github/workflows",
    r"MANIFEST.in",
    r"setup.py",
    r"setup.cfg",
    r"snafu/benchmarks/_[a-z]*.py",
    r"snafu/[a-z]*.py",
    r"tox.ini",
    r"version.txt",
    r"requirements/",
)
IGNORES = (r"Dockerfile\.ppc64le$",)


def get_git_diff(upstream_branch: str) -> str:
    """
    Run git-diff against upstream branch.

    Will pull fetch upstream branch to ensure it can be compared against.

    Arguments
    ---------
    upstream_branch : str
        Upstream branch to compare against.

    Returns
    -------
    str
        Output of git diff
    """

    subprocess.run(shlex.split(f"git fetch origin {upstream_branch}"), check=True)
    completed_process = subprocess.run(
        shlex.split(f"git diff origin/{upstream_branch} --name-only"),
        check=True,
        stdout=subprocess.PIPE,
    )
    return completed_process.stdout.decode("utf-8")


def parse_git_diff(diff_str: str) -> set[str]:
    """
    Return parsed output of `git-diff --name-only`.

    Arguments
    ---------
    diff_str : str
        Output of `git-diff --name-only`.

    Returns
    -------
    set of str
        Unique set of files changed, according to git-diff
    """

    return set(map(str.strip, diff_str.strip().split("\n")))


def get_dockerfile_list() -> str:
    """
    Use the find command to get list of all dockerfiles within snafu.

    Returns
    -------
    str
        Output of find command
    """

    completed_process = subprocess.run(
        shlex.split("find snafu/ -name Dockerfile*"), check=True, stdout=subprocess.PIPE
    )
    return completed_process.stdout.decode("utf-8")


def parse_dockerfile_list(df_list: str) -> set[str]:
    """
    Parse given list of Dockerfiles into a set of str.

    If a given Dockerfile path matches a regex in IGNORES, then the Dockerfile will
    not be included in returned set.

    Arguments
    ---------
    df_list : str
        Dockerfile list to parse. Should be newline-separated list of relative paths from
        project root.

    Returns
    -------
    set of str
        Set of all unique dockerfile paths parsed from given input.
    """

    result = []
    for dockerfile in df_list.strip().split("\n"):
        dockerfile = dockerfile.strip()
        ignored = False
        for ignore in IGNORES:
            if re.search(ignore, dockerfile) is not None:
                ignored = True
                break

        if not ignored:
            result.append(dockerfile)

    return set(result)


@dataclasses.dataclass
class MatrixEntry:
    """
    Entry within the matrix.

    See module docstring for details.
    """

    dockerfile: str
    image_name: str
    benchmark: str
    env_var: str
    archs: Iterable[str]
    changed: bool
    tags: Iterable[str]

    @classmethod
    def new(cls, dockerfile: str, changed: bool, archs: Iterable[str], tags: Iterable[str]) -> "MatrixEntry":
        """
        Create a new instances of the MatrixEntry

        Parameters
        ----------
        dockerfile : str
            Relative path to Dockerfile. Will be used to determine other attributes.
        changed : bool
            Sets the changed attribute.
        archs : list of str
            Sets the archs attribute.
        tags : list of str
            Sets the tags attribute.
        """

        benchmark = str(pathlib.Path(dockerfile).parent.stem).replace("_wrapper", "")
        return cls(
            dockerfile=dockerfile,
            changed=changed,
            archs=archs,
            image_name=benchmark,
            benchmark=benchmark,
            env_var=f"{benchmark.upper()}_IMAGE",
            tags=tags,
        )

    def build_json(self) -> Iterable[dict[str, str | bool]]:
        """Convert the given MatrixEntry into series of JSON-dicts, one for each arch."""

        for arch in self.archs:
            tag_suffix = f"-{arch}"
            yield {
                "dockerfile": self.dockerfile,
                "image_name": self.image_name,
                "benchmark": self.benchmark,
                "env_var": self.env_var,
                "tag_suffix": tag_suffix,
                "arch": arch,
                "changed": self.changed,
                "tags": " ".join([f"{tag}{tag_suffix}" for tag in self.tags]),
            }

    def manifest_json(self) -> Iterable[dict[str, str | bool]]:
        """Convert the given MatrixEntry into series of JSON-dicts, one for each tag."""

        for tag in self.tags:
            tag_suffixes = " ".join([f"-{arch}" for arch in self.archs])
            archs = " ".join(self.archs)
            yield {
                "benchmark": self.benchmark,
                "image_name": self.image_name,
                "dockerfile": self.dockerfile,
                "tag": tag,
                "tag_suffixes": tag_suffixes,
                "changed": self.changed,
                "archs": archs,
            }


class MatrixBuilder:
    """
    Builder for the GHA Jobs Matrix.

    Parameters
    ----------
    archs : iterable of str
        List of architectures to build against. Will create a matrix entry for each architecture for each
        Dockerfile.
    tags : iterable of str
        List of tags that will be applied to the built images.
    bones : iterable of str
        List of regex strings to match paths against to determine if the path is a snafu "bone".
    upstream_branch : str
        Upstream branch to compare changes to, in order to determine the value of "changed".
    dockerfile_set : set of str
        Set of dockerfiles within the snafu repository.
    changed_set : set of str
        Set of changed files within the snafu repository.
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        archs: Iterable[str],
        tags: Iterable[str],
        bones: Iterable[str],
        upstream_branch: str,
        dockerfile_set: set[str],
        changed_set: set[str],
    ):
        """Contsruct the matrix builder."""

        self.archs = archs
        self.tags = tags
        self.bones = bones
        self.upstream_branch = upstream_branch
        self.dockerfile_set = dockerfile_set
        self.changed_set = changed_set
        self.manifest_matrix: dict[str, list[dict[str, str | bool]]] = {}
        self.build_matrix: dict[str, list[dict[str, str | bool]]] = {}

        self.reset()

    def reset(self):
        """Reset the matrix to empty starting point."""
        self.build_matrix = {"include": []}
        self.manifest_matrix = {"include": []}

    def add_entry(self, entry: MatrixEntry):
        """Add the given MatrixEntry into the jobs matrix."""

        for json_dict in entry.build_json():
            self.build_matrix["include"].append(json_dict)
        for json_dict in entry.manifest_json():
            self.manifest_matrix["include"].append(json_dict)

    def bones_changed(self) -> bool:
        """Return True if a bone has is found in the changed set."""

        for bone in self.bones:
            bone_regex = re.compile(bone)
            for changed in self.changed_set:
                if bone_regex.search(changed) is not None:
                    return True
        return False

    def benchmark_changed(self, dockerfile: str) -> bool:
        """Return True if the given dockerfile's benchmark has changed."""

        dockerfile_dir = pathlib.Path(dockerfile).parent
        for changed in self.changed_set:
            try:
                pathlib.Path(changed).relative_to(dockerfile_dir)
            except ValueError:
                pass
            else:
                return True
        return False

    def build(self, changed_only: bool = True):
        """
        Build the GHA jobs matrix.

        Parameters
        ----------
        changed_only : bool, optional
            If True, then only dockerfiles that are considered changed will be added into the matrix.
            Defaults to True.
        """

        bones_changed = self.bones_changed()
        for dockerfile in self.dockerfile_set:
            changed = bones_changed or self.benchmark_changed(dockerfile)
            if (changed_only and changed) or not changed_only:
                entry = MatrixEntry.new(
                    dockerfile=dockerfile, archs=self.archs, changed=changed, tags=self.tags
                )
                self.add_entry(entry)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tags", nargs="+", help="Tags to apply to the built images")
    parser.add_argument(
        "--upstream",
        default="master",
        help="Upstream branch to compare against. Defaults to 'master'",
    )
    parser.add_argument("--changed-only", action="store_true", help="Only output changed Dockerfiles")
    parser.add_argument(
        "--manifest", action="store_true", help="Output both the build and manifest matrix JSON"
    )
    args = parser.parse_args()
    builder = MatrixBuilder(
        archs=ARCHS,
        tags=args.tags,
        bones=BONES,
        upstream_branch=args.upstream,
        dockerfile_set=parse_dockerfile_list(get_dockerfile_list()),
        changed_set=parse_git_diff(get_git_diff(args.upstream)),
    )
    builder.build(changed_only=args.changed_only)
    if args.manifest:
        print(json.dumps({"build": builder.build_matrix, "manifest": builder.manifest_matrix}))
    else:
        print(json.dumps(builder.build_matrix))
