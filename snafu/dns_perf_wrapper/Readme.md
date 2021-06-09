## DNS Performance Workload Wrapper
Wrapper around [dnsperf](https://github.com/DNS-OARC/dnsperf) to measure throughput ( requests per second ) and latency metrics for Domain Name Service ( DNS ). The collected metrics are scraped to generate a json which can be indexed into Elasticsearch datastore.


### Dependencies
This wrapper requires a couple of dependencies as well as enabling copr repo to download the latest dnsperf package. For more details [see[(https://github.com/DNS-OARC/dnsperf/blob/master/README.md). It's recommended to build and run the [containerized version](Dockerfile) to avoid managing the installation on the host. Here are the dependencies which need to be installed when running the standalone version:
- python3
- python3-pip
- openssl-devel
- epel-release
- ck-devel
- yum-plugin-copr
- dnsperf ( Run $ dnf copr enable @dnsoarc/dnsperf and $ dnf install dnsperf to enable the repo to install it )


### Run
```
usage: run_snafu [-h] [-v] -t TOOL [--run-id [RUN_ID]] -u UUID --server-address SERVER_ADDRESS --queries-per-second QUERIES_PER_SECOND --run-time RUN_TIME --data-file DATA_FILE [--clients CLIENTS]

DNS perf workload Wrapper script

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         enables verbose wrapper debugging info (default: 20)
  -t TOOL, --tool TOOL  Provide tool name (default: None)
  --run-id [RUN_ID]     Run ID to unify benchmark results in ES (default: NA)

DNS Perf:
  -u UUID, --uuid UUID  Provide the uuid (default: None)
  --server-address SERVER_ADDRESS
                        DNS server address to send the requests (default: None)
  --queries-per-second QUERIES_PER_SECOND
                        Number of queries per second (default: None)
  --run-time RUN_TIME   run for at most this many seconds (default: None)
  --data-file DATA_FILE
                        File path with the records to send as queries to the server (default: None)
  --clients CLIENTS     The number of clients to act as (default: 1)
```

Note that file location passed through --data-file variable is where the records are defined. For example:
```
www.google.com A
www.gmail.com A
chat.google.com A
mail.google.com A
drive.google.com A
docs.google.com A
meet.google.com A
sites.google.com A
plus.google.com A
```

### Metrics
The wrapper runs dnsperf and generates a json document with the results as well as the input configuration/parameters. Benchmark wrapper also wraps around metadata to be indexed into Elasticsearch as explained [here](https://github.com/cloud-bulldozer/benchmark-wrapper#how-do-i-post-results-to-elasticsearch-from-my-wrapper). Here is a sample results document:

```
{
    "_index": "snafu-dns_perf-results",
    "_op_type": "create",
    "_source": {
        "uuid": "0f038d28-ef3a-42c0-aea3-435d19686ab1",
        "cluster_name": "mycluster",
        "clients": 1,
        "timestamp": "2021-05-21T16:45:15",
        "elapsed_time": 6.012354850769043,
        "latency_stddev": 0.003623,
        "avg_latency": 0.010767,
        "latency_min": 0.006275,
        "latency_max": 0.017417,
        "QPS": 19.999643,
        "runtime": 6.000107,
        "avg_request_packet_size": 32.0,
        "avg_response_packet_size": 60.0,
        "queries_lost": 0,
        "queries_lost_percentage": 0.0,
        "queries_completed": 120,
        "queries_completed_percentage": 100.0,
        "queries_sent": 120,
        "stop_time_duration": 6.0,
        "dns_address": "8.8.8.8:53",
        "dnsperf_version": "2.5.2",
        "run_id": "NA"
    },
    "_id": "18cdda19f6d15c6dab17c6da7fa1422f007057a193b25d298439225c0325ce8f",
    "run_id": "NA"
}

```
