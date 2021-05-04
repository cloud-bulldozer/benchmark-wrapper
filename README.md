# Benchmark-Wrapper aka SNAFU - Situation Normal: All F'ed Up

Most Performance workload tools were written to tell you the performance at a given time under given circumstances.

These scripts are to help enable these legacy tools store their data for long term investigations.

Note: SNAFU does not depend upon Kubernetes, so you can use run_snafu.py on a bare-metal or VM cluster without relying
on Kubernetes to start/stop pods.  So if you need your benchmark to collect data for both Kubernetes and non-Kubernetes
environments, develop in SNAFU and then write benchmark-operator benchmark to integrate with Kubernetes.

## What workloads do we support?

| Workload                       | Use                    | Status             |
| ------------------------------ | ---------------------- | ------------------ |
| UPerf                          | Network Performance    | Working            |
| flent                          | Network Performance    | Working            |
| fio                            | Storage IO             | Working            |
| YCSB                           | Database Performance   | Working            |
| Pgbench                        | Postgres Performance   | Working            |
| smallfile                      | metadata-intensive ops | Working            |
| fs-drift                       | metadata-intensive mix | Working            |
| cyclictest                     | Real-Time Latency      | Working            |
| oslat                          | Real-Time Latency              | Working            |
| OpenShift Upgrade              | Time to upgrade                | Working            |
| OpenShift Scaling              | Time to scale                  | Working            |
| Log Generator                  | Log throughput to backend      | Working            |
| Image Pull                     | Time to copy from a container image from a repo | Working |
| DNS-Perf                       | DNS Performance                | Working            |
    
## What backend storage do we support?

| Storage        | Status   |
| -------------- | -------- |
| Elasticsearch  | Working  |
| Prom           | Planned  |


It is suggested to use a venv to install and run snafu.

```
python3 -m venv /path/to/new/virtual/environment
source /path/to/new/virtual/environment/bin/activate
git clone https://github.com/cloud-bulldozer/snafu
python setup.py develop
run_snafu --tool Your_Benchmark ...
```


## how do I develop a snafu extension for my benchmark?

In what follows, your benchmark's name should be substituted for the name "Your_Benchmark".  Use alphanumerics and
underscores only in your benchmark name.

You must supply a "wrapper", which provides these functions:
* build the container image for your benchmark, with all the packages, python modules, etc. that are required to run it.
* runs the benchmark and stores the benchmark-specific results to an elasticsearch server

Note: snafu is a python library, so please add the new python libraries you import
to the setup.txt

Your benchmark-operator benchmark will define several environment variables relevant to Elasticsearch:
* es - URL of elasticsearch instance. i.e. https://elastic.instance.domain.com:9200
* es_verify_cert - Verify ElasticSearch TLS certificate, by default `true`
* es_index - OPTIONAL - default is "snafu-tool" - define the prefix of the ES index name

It will then invoke your wrapper via the command:

```
run_snafu --tool Your_Benchmark ...
```

Additional parameters are benchmark-specific and are passed to the wrapper to be parsed, with the exception of some
common parameters:

* --tool - which benchmark you want to run
* --verbose - turns on DEBUG-level logging, including ES docs posted
* --samples - how many times you want to run the benchmark (for variance measurement)
* --dir -- where results should be placed

Create a subdirectory for your wrapper with the name Your_Benchmark_wrapper.   The following files must be present in
it:

* Dockerfile - builds the container image in quay.io/cloud-bulldozer which benchmark-operator will run
* \_\_init\_\_.py - required so you can import the python module
* Your_Benchmark_wrapper.py - run_snafu.py will run this (more later on how)
* trigger_Your_Benchmark.py - run a single sample of the benchmark and generate ES documents from that

In order for run_snafu.py to know about your wrapper, you must add an import statement and a key-value pair for your
benchmark to utils/wrapper_factory.py.

The Dockerfile should *not* git clone snafu - this makes it harder to develop wrappers. Instead, assume that the image
will be built like this:

```
# docker build -f snafu/Your_Benchmark_wrapper/Dockerfile .
```

And use the Dockerfile command:

```
RUN mkdir -pv /opt/snafu
COPY . /opt/snafu/
```

The end result is that your benchmark-operator benchmark becomes much simpler while you get to save data to a central Elasticsearch
server that is viewable with Kibana and Grafana!

Look at some of the other benchmarks for examples of how this works.

## How do I post results to Elasticsearch from my wrapper?

Every snafu benchmark will use Elasticsearch index name of the form **orchestrator-benchmark-doctype**, consisting of the 3
components:

* orchestrator - software running the benchmark - usually "benchmark-operator" at this point
* benchmark - typically the tool name, something like "iperf" or "fio"
* doctype - type of documents being placed in this index.

If you are using run_snafu.py, construct an elastic search document in the usual way, and then use the python "yield" statement (do not return!) a **document** and **doctype**, where **document** is a python dictionary representing an Elasticsearch document, and **doctype** is the end of the index name.  For example, any benchmark-operator benchmark will be defining an index name that begins with benchmark-operator, but your wrapper can create whatever indexes it wants with that prefix.  For example, to create an index named benchmark-operator-iperf-results, you just do something like this:

- optionally, in roles/your-benchmark/defaults/main.yml, you can override the default if you need to:

```
es_index: benchmark-operator-iperf
```

- in your snafu wrapper, to post a document to Elasticsearch, you **MUST**:

```
    yield my_doc, 'results'
```

run_snafu.py concatenates the doctype with the es_index component associated with the benchmark to generate the
full index name, and posts document **my__doc** to it.

## how do I integrate snafu wrapper into my benchmark-operator benchmark?

You just replace the commands to run the workload in your benchmark-operator benchmark
(often in roles/Your_Workload/templates/workload.yml.j2) with the command below.

First, you have to define environment variables used to pass information to
run_snafu.py for access to Elasticsearch:



```
      spec:
        containers:
          env:
          - name: uuid
            value: "{{ uuid }}"
          - name: test_user
            value: "{{ test_user }}"
          - name: clustername
            value: "{{ clustername }}"
{% if elasticsearch.server is defined %}
          - name: es
            value: "{{ elasticsearch.server }}"
{% endif %}
```

Note that you do not have to use elasticsearch with benchmark-operator, but this is recommended
so that your results will be accessible outside of the openshift cluster in which
they were created.

Next you replace the commands that run your workload with a single command to invoke
run_snafu.py, which in turn invokes the wrapper to run the workload for as many samples
as you want.

```
...
                 args:
...
                    run_snafu
                   --tool Your_Workload
{% if Your_Workload.samples is defined %}
                   --samples {{Your_Workload.samples}}
{% endif %}
```

The remaining parameters are specific to your workload and wrapper.  run_snafu.py
has an "object-oriented" parser - the only inherited parameter is the --tool parameter.
run_snafu.py uses the tool parameter to determine which wrapper to invoke, and
The remaining parameters are defined and parsed by the workload-specific wrapper.


## how do I run my snafu wrapper in CI?

add the ci_test.sh script to your wrapper directory - the SNAFU CI (Continuous Integration) test harness
will automatically find it and run it.   This assumes that your wrapper supports benchmark-operator, for now.
At present, the CI does not test SNAFU on baremetal but this may be added in the future.

every ci_test.sh script makes use of environment variables defined in ci/common.sh :

* RIPSAW_CI_IMAGE_LOCATION - defaults to quay.io
* RIPSAW_CI_IMAGE_ACCOUNT - defaults to rht_perf_ci
* SNAFU_IMAGE_TAG (defaults to snafu_ci)
* SNAFU_IMAGE_BUILDER (defaults to podman, can be set to docker)

You, the wrapper developer, can override these variables to use any container image repository
supported by benchmark-operator (quay.io is at present the only location tested).

NOTE: at present, you need to force these images to be public images so that minikube can
load them. A better method is needed.

In your CI script, ci_test.sh, you can make use of these 2 environment variables:

* SNAFU_IMAGE_TAG (defaults to snafu_ci)
* SNAFU_WRAPPER_IMAGE_PREFIX - just concatenation of location and account

And here is a simple example of a ci_test.sh (they all look very similar):

```
#!/bin/bash
source ci/common.sh
default_image_spec="quay.io/cloud-bulldozer/your_wrapper:master"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/your_wrapper:$SNAFU_IMAGE_TAG
build_and_push snafu/your_wrapper/Dockerfile $image_spec

cd benchmark-operator
sed -i "s#$default_image_spec#$image_spec#" roles/your_wrapper_in_benchmark-operator/templates/*

# Build new benchmark-operator image
update_operator_image

# run the benchmark-operator CI for your wrapper in tests/ and get resulting UUID
get_uuid test_your_wrapper.sh
uuid=`cat uuid`

cd ..

# Define index (there can be more than 1 separated by whitespaces)
index="benchmark-operator-your-wrapper-results"

check_es "${uuid}" "${index}"
exit $?
```

Note: If your PR requires a PR in benchmark-operator to be merged, you can ask CI to
checkout that PR by adding a `Depends-On: <benchmark-operator_pr_number>` to the end of
your snafu commit message.

## CodeStyling and Linting

Touchstone uses [pre-commit](https://pre-commit.com) framework to maintain the code linting and python code styling.
The CI would run the pre-commit check on each pull request.
We encourage our contributors to follow the same pattern, while contributing to the code.

The pre-commit configuration file is present in the repository `.pre-commit-config.yaml`
It contains the different code styling and linting guide which we use for the application.

Following command can be used to run the pre-commit:
`pre-commit run --all-files`

If pre-commit is not installed in your system, it can be install with : `pip install pre-commit`
