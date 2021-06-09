<!--- Documentation homepage --->

# benchmark-wrapper

**benchmark-wrapper**, aka, **Situation Normal: All F'ed Up (snafu)**, provides a convenient mechanism for launching, processing, and storing data produced by performance benchmarks. Traditionally, benchmark tools have presented users with the following challenges:

1. Ad hoc and/or raw standard output.
2. No method for preserving and exporting results for long term archive.
3. Difficulty at being platform agnostic.

benchmark-wrapper aims to solve these issues by providing a common, streamlined interface for running any performance benchmark required and exporting the results as needed.

The architecture is simple. Let's say that a user wants to run the totally-awesome benchmark, which runs on the CLI and has its own special output format. We start by creating a Python module (referred to as a wrapper), which can understand how to run totally-awesome, interpret its output, and transform the results into JSON-formatted events:

When we then run snafu, it begins by processing user input and ensuring that the specified export locations are up and running. For instance, a user can specify they wish to run the totally-awesome workload with 500 samples, 4 CPU cores, and export the results to an Elasticsearch instance running on localhost. snafu will ensure that all the required arguments for the totally-awesome workload are present and check that the ES instance on localhost is available. After pre-flight checks are complete, snafu will load the totally-awesome wrapper Python module, use it to perform the benchmark, collect the results and export.


A suite of benchmarks comes supported out-of-the-box.

<!--- Table of Contents Sidebar --->
```{toctree}
install
examples
usage
workloads
exports
design
contributing
```
