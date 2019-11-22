# SNAFU - Situation Normal: All F'ed Up

Most Performance workload tools were written to tell you the performance at a given time under given circumstances.

These scripts are to help enable these legacy tools store their data for long term investigations.

Note: SNAFU does not depend upon Kubernetes, so you can use run_snafu.py on a bare-metal or VM cluster without relying
on Kubernetes to start/stop pods.  So if you need your benchmark to collect data for both Kubernetes and non-Kubernetes
environments, develop in SNAFU and then write ripsaw benchmark to integrate with Kubernetes.

## What workloads do we support?

| Workload                       | Use                    | Status             |
| ------------------------------ | ---------------------- | ------------------ |
| UPerf                          | Network Performance    | Working            |
| fio                            | Storage IO             | Working            |
| YCSB                           | Database Performance   | Working            |
| Pgbench                        | Postgres Performance   | Working            |
| smallfile                      | metadata-intensive ops | Working            |
| fs-drift                       | metadata-intensive mix | Working            |

## What backend storage do we support?

| Storage        | Status   |
| -------------- | -------- |
| Elasticsearch  | Working  |
| Prom           | Planned  |

## how do I develop a snafu extension for my benchmark?

In what follows, your benchmark's name should be substituted for the name "Your_Benchmark".  Use alphanumerics and
underscores only in your benchmark name.

You must supply a "wrapper", which provides these functions:
* build the container image for your benchmark, with all the packages, python modules, etc. that are required to run it.
* runs the benchmark and stores the benchmark-specific results to an elasticsearch server

Your ripsaw benchmark will define several environment variables relevant to Elasticsearch:
* es - hostname of elasticsearch server
* es_port - port number of elasticsearch server (default 9020)
* es_index - OPTIONAL - default is "ripsaw-tool" - define the prefix of the ES index name

It will then invoke your wrapper via the command:

```
python run_snafu.py --tool Your_Benchmark ...
```

Additional parameters are benchmark-specific and are passed to the wrapper to be parsed, with the exception of some
common parameters:

* --tool - which benchmark you want to run
* --verbose - turns on DEBUG-level logging, including ES docs posted
* --samples - how many times you want to run the benchmark (for variance measurement)
* --dir -- where results should be placed

Create a subdirectory for your wrapper with the name Your_Benchmark_wrapper.   The following files must be present in
it:

* Dockerfile - builds the container image in quay.io/cloud-bulldozer which ripsaw will run
* \_\_init\_\_.py - required so you can import the python module
* Your_Benchmark_wrapper.py - run_snafu.py will run this (more later on how)
* trigger_Your_Benchmark.py - run a single sample of the benchmark and generate ES documents from that

In order for run_snafu.py to know about your wrapper, you must add an import statement and a key-value pair for your
benchmark to utils/wrapper_factory.py.

The Dockerfile should *not* git clone snafu - this makes it harder to develop wrappers.   Instead, assume that the image
will be built like this:

```
# docker build -f Your_Benchmark_wrapper/Dockerfile .
```

And use the Dockerfile command:

```
RUN mkdir -pv /opt/snafu
COPY . /opt/snafu/
```

The end result is that your ripsaw benchmark becomes much simpler while you get to save data to a central Elasticsearch
server that is viewable with Kibana and Grafana!

Look at some of the other benchmarks for examples of how this works.

## how do I post results to Elasticsearch from my wrapper?

Every snafu benchmark will use Elasticsearch index name of the form **orchestrator-benchmark-doctype**, consisting of the 3
components:

* orchestrator - software running the benchmark - usually "ripsaw" at this point
* benchmark - typically the tool name, something like "iperf" or "fio"
* doctype - type of documents being placed in this index.

If you are using run_snafu.py, construct an elastic search document in the usual way, and then use the python "yield" statement (do not return!) a **document** and **doctype**, where **document** is a python dictionary representing an Elasticsearch document, and **doctype** is the end of the index name.  For example, any ripsaw benchmark will be defining an index name that begins with ripsaw, but your wrapper can create whatever indexes it wants with that prefix.  For example, to create an index named ripsaw-iperf-results, you just do something like this:

- optionally, in roles/your-benchmark/defaults/main.yml, you can override the default if you need to:

```
es_index: ripsaw-iperf
```

- in your snafu wrapper, to post a document to Elasticsearch, you **MUST**:

```
    yield my_doc, 'results'
```

run_snafu.py concatenates the doctype with the es_index component associated with the benchmark to generate the
full index name, and posts document **my__doc** to it.

## how do I integrate snafu wrapper into my ripsaw benchmark?

You just replace the commands to run the workload in your ripsaw benchmark 
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
          - name: es_port
            value: "{{ elasticsearch.port }}"
{% endif %}
```

Note that you do not have to use elasticsearch with ripsaw, but this is recommended
so that your results will be accessible outside of the openshift cluster in which
they were created.

Next you replace the commands that run your workload with a single command to invoke
run_snafu.py, which in turn invokes the wrapper to run the workload for as many samples
as you want.

```
...
                 args:
...
                   python run_snafu.py
                   --tool Your_Workload
{% if Your_Workload.samples is defined %}
                   --samples {{Your_Workload.samples}}
{% endif %}
```

The remaining parameters are specific to your workload and wrapper.  run_snafu.py
has an "object-oriented" parser - the only inherited parameter is the --tool parameter.
run_snafu.py uses the tool parameter to determine which wrapper to invoke, and
The remaining parameters are defined and parsed by the workload-specific wrapper.

