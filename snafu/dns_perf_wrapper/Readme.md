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
- dnsperf ( Run $ dnf copr enable @dnsoarc/dnsperf to enable the repo to install it )


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
        "timestamp": "2021-04-29T19:17:47",
        "elapsed_time": 6.0132739543914795,
        "latency_stddev": "0.003210",
        "avg_latency": "0.012043",
        "QPS": "19.999700",
        "runtime": "6.000090",
        "avg_request_packet_size": "32",
        "avg_response_packet_size": "60",
        "queries_lost": "0",
        "queries_lost_percentage": "0.00%",
        "queries_completed": "120",
        "queries_completed_percentage": "100.00",
        "queries_sent": "120",
        "stop_time": "6.000000",
        "dns_host": "8.8.8.8:53",
        "dnsperf_version": "2.5.2",
        "run_id": "NA"
    },
    "_id": "7b492babd92257b3aca2bac5667115cfcf821ca54d0ce5c61360bb085fe99a7e",
    "run_id": "NA"
}
```
