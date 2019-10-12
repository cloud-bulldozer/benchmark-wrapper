# SNAFU - Situation Normal: All F'ed Up

Most Performance workload tools were written to tell you the performance at a given time under given circumstances.

These scripts are to help enable these legacy tools store their data for long term investigations.

## What workloads do we support?

| Workload                       | Use                    | Status             |
| ------------------------------ | ---------------------- | ------------------ |
| UPerf                          | Network Performance    | Working            |
| fio                            | Storage IO             | Working            |
| YCSB                           | Database Performance   | Working            |
| Pgbench                        | Postgres Performance   | Working            |


## What backend storage do we support?

| Storage        | Status   |
| -------------- | -------- |
| Elasticserach  | Working  |
| Prom           | Planned  |

## how do I develop a snafu extension for my benchmark?

In what follows, your benchmark's name should be substituted for the name "Your_Benchmark".  Use alphanumerics and
underscores only in your benchmark name.

You must supply a "wrapper", which provides these functions:
* build the container image for your benchmark, with all the packages, python modules, etc. that are required to run it.
* runs the benchmark and stores the benchmark-specific results to an elasticsearch server

Your ripsaw benchmark will define several environment variables:
* es - hostname of elasticsearch server
* es_port - port number of elasticsearch server (default 9020)
* es_index - prefix of index name for your results in elasticsearch (default "ripsaw")

It will then invoke your wrapper via the command:

```
python run_snafu.py --tool Your_Benchmark ...
```

Additional parameters are benchmark-specific and are passed to the wrapper to be parsed, with the exception of some
common parameters:

* --tool - which benchmark you want to run
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

Note: Please tag @aakarshg for review when adding a new benchmark wrapper especially ones that index data into elasticsearch and mention:
* which field(key) in the document will be of the type date(time)
* highly recommend that the key of the type date(time) use epoch format (helps a lot when dealing with tool run in multiple timezones like snafu)

## how do I integrate snafu wrapper into my ripsaw benchmark?

You just replace the commands to run the workload in your ripsaw benchmark
(often in roles/Your_Workload/templates/workload.yml.j2) with the command below.

First, you have to define environment variables used to pass information to
run_snafu.py for access to Elasticsearch:



```
      spec:
        containers:
          env:
{% if es_server is defined %}
          - name: uuid
            value: "{{ uuid }}"
          - name: test_user
            value: "{{ test_user }}"
          - name: clustername
            value: "{{ clustername }}"
          - name: es
            value: "{{ es_server }}"
          - name: es_port
            value: "{{ es_port }}"
          - name: es_index
            value: "{{ es_index }}"
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
