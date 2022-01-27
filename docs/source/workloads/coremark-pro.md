# CoreMark-Pro

Wrapper for [CoreMark-Pro](https://github.com/eembc/coremark-pro) which is a CPU benchmarking tool that provides a single number score for easy comparison across runs.

## Overview of Operations

- A path to where CoreMark-Pro has been cloned is provided to benchmark-wrapper since there is no install
mechanism.
- Executing the benchmark is done with `make` and also compiles the benchmark if not already done.
- A log folder is created from the exection, where only the `.log` and `.mark` file are processed:

  ```
  coremark-pro/builds/linux64/gcc64/logs
  ├── linux64.gcc64.log       # Raw logs of the CoreMark Pro run
  ├── linux64.gcc64.mark      # Results: both individual workloads and overall score
  ├── progress.log            # Does not process
  ├── zip-test.run.log        # Does not process
  └── zip-test.size.log       # Does not process
  ```
- The results are ingested into two different Elasticsarch indexes:
    - `*-coremark-pro-summary`: Results from the `.mark` file. Provides the calculated results from CoreMark-Pro.
    - `*-coremark-pro-raw`: Raw logs from the `.log` file. Intended for analyzing the logs manually.

## Arguments

### Required

- `-p` / `--path` Directory where CoreMark Pro is located.

### Optional

- `-c` / `--context`: CoreMark Pro's context argument. Defaults to `1`.
- `-w` / `--worker`: CoreMark Pro's worker argument. Defaults to `1`.
- `-s` / `--sample`: Number of samples to run. Defaults to `1`.
- `-r` / `--result-name`: The name of CoreMark Pro's result files. This includes the path relative to `--path` and does not include the extension. Defaults to `builds/linux64/gcc64/logs/linux64.gcc64`
- `-i` / `--ingest`: Parses and ingest existing results in a CoreMark-Pro log directory. No support for multiple samples and `date` is based on when benchmark-wrapper is run. Mainly used for debugging.


## Running inside a container

The Dockerfile has CoreMark-Pro pre-built and is located at `/coremark-pro/`. This will need
to be passed to benchmark-wrapper with the `--path` command.

Rest of this section will cover common use-cases that need additional parameters.

### Archive file

To create an archive file and make it accessible to the host system, the `WORKDIR` is set to
`/output/` and can be mounted to the host system. Example:

```
podman run -it \
-v ./FOLDER_TO_SAVE_ARCHIVE/:/output/ \
coremark-pro run_snafu -t coremark-pro --path /coremark-pro/ --create-archive \
--archive coremarkpro.archive
```

### Raw logs

To retrieve the raw logs, mount the log folder from CoreMark-Pro to a **dedicated** folder on the host system otherwise all contents of the folder will be **deleted** when CoreMark-Pro is executed. Default folder is
`/coremark-pro/builds/linux64/gcc/logs/`.

Example of logs folder being saved to a `output` folder in the current directory:

```
podman run -it \
-w /coremark-pro/builds/linux64/gcc64/logs/ \
-v ./output/:/coremark-pro/builds/linux64/gcc64/logs/ \
coremark-pro run_snafu -t coremark-pro -p /coremark-pro/
```

## Parsing

This section gives a general idea of how CoreMark-Pro output matches with the Elasticsearch fields.

### Results

These results are calculated by CoreMark-Pro and read from the `*.mark` file. Each row of the table is ingested as its own record.

#### Example `.mark` file

```
WORKLOAD RESULTS TABLE

                                                 MultiCore SingleCore
Workload Name                                     (iter/s)   (iter/s)    Scaling
----------------------------------------------- ---------- ---------- ----------
cjpeg-rose7-preset                                  178.57     192.31       0.93

.... truncated rest of the workloads ...

MARK RESULTS TABLE

Mark Name                                        MultiCore SingleCore    Scaling
----------------------------------------------- ---------- ---------- ----------
CoreMark-PRO                                       5708.35    5714.89       1.00
```

#### Benchmark-wrapper's archive file output

```
{
    "_source": {
        "test_config": {
            "worker": 1,                     # `--worker`
            "context": 1                     # `--context`
            "sample": 1,                     # `--sample`
        },
        "date": "2021-10.1..",               # Time when benchmark-wrapper was executed.
        "sample": 1,                         # `--sample`
        "name": "cjpeg-rose7-preset,         # Name of the CoreMark-Pro workload
        "multicore": 178.57,                 # Multi Core result
        "singlecore": 192.31,                # Single Core result
        "scaling": 0.93,                     # Scaling result
        "type": "workload",                  # Type of result, determined by the table header
                                             # - `workload`: Data from 'Workload Results Table'
                                             # - `mark`: Data from 'Mark Results Table'
        "cluster_name": "laptop",
        "user": "ed",
        "uuid": "3cc2e4a9-bd7f-4394-8d8c-66415ceeb02f",
        "workload": "coremark-pro",
        "run_id": "NA"
    },
}

... The above is repeated for the rest of the workloads and the mark result ...

```

### Raw logs

These are the raw logs parsed from the `.log` file. The median results are dropped since they can be derived using Elasticsearch. Each row of results is ingested as its own record.


#### Excerpt of a log file

```
#UID            Suite Name                                     Ctx Wrk Fails       t(s)       Iter     Iter/s  Codesize   Datasize
#Results for verification run started at 21285:10:58:22 XCMD=-c1 -w0
236760500         MLT cjpeg-rose7-preset                         1   1     0      0.010          1     100.00    105616     267544
#Results for performance runs started at 21285:10:58:23 XCMD=-c1 -w0
236760500         MLT cjpeg-rose7-preset                         1   1     0      0.081         10     123.46    105616     267544
... truncated rest of the log ...
```

CoreMark-Pro performs two sets of runs for each workload that are marked by the same `uid`.  Each set of runs has a single verification run and three performance runs. The number of runs is non-configurable. Structure of the runs:
```
Set 1: Context = 1 Workload = 1
├─── Workload Verification Run
├─── Performance run #1
├─── Performance run #2
└─── Performance run #3

... Repeat for all workloads ...

Set 2: Context and workload specified by user through -w / -c
├─── Workload Verification Run
├─── Performance run #1
├─── Performance run #2
└─── Performance run #3

... Repeat for all workloads ...

```
#### Benchmark-wrapper's archive file output

A `run_index` field was added to ensure performance runs with the same results are not marked as duplicates.

```
{
    "_source": {
        ## Same as the `.mark` file
        "test_config": {
            "worker": 1,,
            "context": 1,
            "sample": 1
        },
        "date": "2021-10.1..",        # Time when benchmark-wrapper was executed.
        "sample": 1,

        ## Results from the logs
        "uid": "236760500",           # A UID generated per workload by CoreMark-Pro
        "suite": "MLT",
        "name": "cjpeg-rose7-preset",
        "ctx": 1,
        "wrk": 1,
        "fails": 0,
        "t(s)": 0.01,
        "iter": 1,
        "iter/s": 100.0,
        "codesize": 105616,
        "datasize": 267544,
        "type": "verification",       # Possible types: verification / performance
        "starttime": "2021-10....",   # The start time for the runs as recorded by CoreMark Pro
        "run_index": 0,               # An index of how many runs of the same type. Always
                                      # 0 for verification, between 0-2 for performance runs.

        ## Same as the `.mark` file
        "cluster_name": "laptop",
        "user": "ed",
        "uuid": "816f7fe9-ab04-45a4-8a1f-ce61c2fe11e6",
        "workload": "coremark-pro",
        "run_id": "NA"
    },
}
```
## Limitations

- Limited ability to visualize the data from `*-coremark-pro-raw`, requires additional fields to aggregate the runs.
