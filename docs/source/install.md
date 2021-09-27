# Installation

Installing benchmark-wrapper is all done through pip and git, requiring Python >= 3.6. For instance, to download benchmark-wrapper and install within a new virtual environment:

```console
$ git clone https://github.com/cloud-bulldozer/benchmark-wrapper
$ cd benchmark-wrapper
$ python -m venv ./venv
$ pip install .
```

Or, if you want to just install benchmark-wrapper directly into your user site-packages:

```console
$ pip install git+https://github.com/cloud-bulldozer/benchmark-wrapper
```

For reproducable installations, use the appropriate pip requirements files for your target version of Python. These requirement files are generating using [pip-compile](https://pypi.org/project/pip-tools/) and include dependencies pinned to a specific version. Only after testing are these versions upgraded, preventing errors arising from dependency resolution. As an example, to install benchmark-wrapper for Python 3.6:

```console
$ git clone https://github.com/cloud-bulldozer/benchmark-wrapper
$ cd benchmark-wrapper
$ pip install -r requirements/py36-reqs/install.txt
$ pip install .
```

A containerized version of benchmark-wrapper for each workload can also be built using the included Dockerfiles. Each workload is shipped with its own Dockerfile that packages benchmark-wrapper and any tools the benchmark needs to run. These are included under each benchmark's wrapper package within the source code:

```console
$ cd benchmark-wrapper
$ find . -name Dockerfile
```

The build context for these Dockerfiles is the project root, so be sure to take this into consideration when building images. For instance, to build the Uperf benchmark container:

```console
$ cd benchmark-wrapper
$ podman build . -t my-uperf-container -f snafu/benchmarks/uperf/Dockerfile
```

These images are automatically built on merges to our main branch and published to quay over at [quay.io/cloud-bulldozer](https://quay.io/organization/cloud-bulldozer).
