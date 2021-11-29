# uncomment the next line to enable running script directly from shell
##!/usr/bin/python3
#
# script to calculate statistics from raw elasticsearch results
# generated by benchmark-wrapper run_snafu
#
# for example, to find uuids to run this program against, do (after adjusting date):
#   python3 snafu/utils/query_result_uuids.py ripsaw-fio-results date 2021-09-01

import json
import sys
from os import getenv
import numpy

from snafu.utils.fetch_es_test_results import connect_es, result_generator_for_uuid

KiB_per_MiB = 1 << 10
msec_per_sec = 1000.0

class FioStatException(Exception):
    pass


index_name = "ripsaw-fio-results"
# used by strptime()
datetime_format = "%Y-%m-%dT%H:%M:%S.%f%z"

if len(sys.argv) < 2:
    print("ERROR: must supply uuid of test")
    sys.exit(1)

uuid = sys.argv[1]
print("uuid is %s" % uuid)

uuid_query = {
    "query": {"simple_query_string": {"query": uuid, "fields": ["uuid"], "default_operator": "and"}}
}

es = connect_es(es_url=getenv('ES_SERVER'))

optype_dict = {}
max_sample = 0
pods_per_run = None
numjobs = None
iosize_count = 0

hit_generator = result_generator_for_uuid(es, index_name, uuid)
for hit in hit_generator:
    src = hit["_source"]
    uuid_found = src["uuid"]

    #print(json.dumps(src, indent=2))

    # skip All Clients record since we want to add them up ourselves

    jobname = src['fio']['jobname']
    if jobname == 'All clients':
        continue

    # extract fields from document

    numjobs_str = src['global_options']['numjobs']
    if numjobs is None:
        numjobs = int(numjobs_str)
    elif int(numjobs_str) != numjobs:
        raise FioStatException('numjobs in this document does not match others: %s' % str(src))

    sample = int(src["sample"])
    if max_sample < sample:
        max_sample = sample

    optype = src['fio']['job options']['rw']
    if optype != "randread" and optype != "randwrite" and optype != "read" and optype != "write":
        raise FioStatException('unrecognized operation type for document: %s' % str(src))

    # remove "KiB" from end of bs string
    io_size_KiB = int(src['global_options']['bs'][:-3])

    if optype == "randread":
        result_thru = src['fio']['read']
    else:
        result_thru = src['fio']['write']
    iops = float(result_thru['iops'])
    MiB_per_sec = float(result_thru['bw']) / KiB_per_MiB

    elapsed = float(src['fio']['job_runtime']) / msec_per_sec

    # host is really pod name
    host = src['fio']['hostname']

    if pods_per_run == None:
        pods_per_run = len(src['hosts'])

    # build up a tree optype -> iosize -> sample -> pod
    # so we can compute stats

    # optype layer
    try:
        optype_iosizes = optype_dict[optype]
        if iosize_count < len(optype_iosizes):
            iosize_count = len(optype_iosizes)
    except KeyError:
        optype_iosizes = {}
        optype_dict[optype] = optype_iosizes

    # iosize layer
    try:
        iosize_samples = optype_iosizes[io_size_KiB]
    except KeyError:
        iosize_samples = {}
        optype_iosizes[io_size_KiB] = iosize_samples

    # sample layer
    try:
        sample_pods = iosize_samples[sample]
    except KeyError:
        sample_pods = {}
        iosize_samples[sample] = sample_pods

    # pod layer
    tupl = (elapsed, MiB_per_sec, iops)
    try:
        no_tupl = sample_pods[host]
        raise FioStatException("for optype %s and sample %d, pod IP %s collides with previous pod document" % 
            (optype, sample, host))
    except KeyError:
        # expected outcome
        sample_pods[host] = tupl

# now validate data

print("optypes in test: %s" % str(optype_dict.keys()))
print("")

print(
    "   optype, io-size-KiB, sample, pod,                            IOPS, MiB/s, elapsed, %dev"
)
for optype in sorted(optype_dict.keys()):
    optype_iosizes = optype_dict[optype]
    iosizes_keys = optype_iosizes.keys()
    if len(iosizes_keys) < iosize_count:
        print(
            "WARNING: only %d io sizes for optype %s"
            % (len(iosizes_keys), optype)
        )
    for iosize_key in sorted(iosizes_keys):
      iosize_samples = optype_iosizes[iosize_key]
      sample_list_keys = sorted(iosize_samples.keys())
      if len(sample_list_keys) < max_sample:
        print(
            "WARNING: op-type %s does not have %d samples, has only %d samples"
            % (optype, max_sample, len(sample_list_keys))
        )
      iops_samples = []
      for s in sorted(sample_list_keys):
        sample_pods = iosize_samples[s]
        sample_pods_keys = sample_pods.keys()
        if len(sample_pods_keys) != numjobs * pods_per_run:
            print(
                "WARNING: only %d pods found in optype %s sample %d, expected %d"
                % (len(sample_pods_keys), optype, s, numjobs)
            )
        total_MiB_per_sec = 0.0
        total_iops = 0.0
        elapsed_times = []
        for p in sorted(sample_pods_keys):
                (elapsed, MiB_per_sec, iops) = sample_pods[p]
                total_MiB_per_sec += MiB_per_sec
                total_iops += iops
                print(
                    "%10s, %8d, %2d, %-40s, %f, %f, %f"
                    % (optype, iosize_key, s, p, iops, MiB_per_sec, elapsed)
                )
                elapsed_times.append(elapsed)
        sample_pods["_MiB_per_sec"] = total_MiB_per_sec
        sample_pods["_iops"] = total_iops
        sample_pods["_elapsed_mean"] = mean_elapsed = sum(elapsed_times) / len(elapsed_times)
        sample_pods["_elapsed_pctdev"] = pctdev = numpy.std(numpy.array(elapsed_times)) * 100.0 / mean_elapsed
        print(
            "%10s, %8d, %2d, %-40s, %f, %f, %f, %f"
            % (
                optype,
                iosize_key,
                s,
                "all-pods",
                total_iops,
                total_MiB_per_sec,
                mean_elapsed,
                pctdev,
            )
        )
        iops_samples.append(total_iops)
      iops_mean_across_samples = numpy.average(iops_samples)
      iops_pctdev_across_samples = 100.0 * numpy.std(iops_samples) / iops_mean_across_samples
      print("%10s, %8d, mean iops %f, %% dev iops %f" 
              % (optype, iosize_key, iops_mean_across_samples, iops_pctdev_across_samples))
      if len(iops_samples) < 3:
        print(
            "WARNING: only %d samples for op %s, percent deviation cannot be measured"
            % (len(iops_samples), optype)
        )
