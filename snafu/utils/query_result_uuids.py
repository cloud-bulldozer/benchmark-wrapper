# uncomment the next line to enable running script directly from the shell
##/usr/bin/python3
#
# script to pull uuids of tests from an index for a time range
# and list them with clustername and user so we can find relevant tests
#
# parameters:
# 1: elastic search result index name
# 2: name of timestamp field within the index documents
# 3: (optional) start time, in datetime_format variable below
# 4: (optional) end time, in datetime_format format variable below

import os
import sys
from datetime import datetime, timezone
from sys import argv

import snafu.utils.fetch_es_test_results

NOTOK = 1


def usage(errmsg):
    print("ERROR: %s" % errmsg)
    print("usage: query_test_uuids.py results-index-name timestamp-fieldname [ start-time [ end-time ]]")
    sys.exit(NOTOK)


if len(argv) < 3:
    usage("too few command line parameters")

index_name = argv[1]
timestamp_fieldname = argv[2]


def compute_query():
    match_all = {"size": 100, "query": {"match_all": {}}}
    query_times = match_all
    if len(argv) > 3:
        starting_time_str = argv[3]
        ending_time_str = "now"
        if len(argv) > 4:
            ending_time_str = argv[4]
        timestamp_range = {
            "query": {
                "range": {
                    "%s"
                    % timestamp_fieldname: {
                        "gte": starting_time_str,
                        "lte": ending_time_str,
                        "relation": "WITHIN",
                    }
                }
            }
        }
        query_times = timestamp_range
    return query_times


es = snafu.utils.fetch_es_test_results.connect_es()

# used by strptime()
datetime_format = "%Y-%m-%dT%H:%M:%S.%f%z"

# dictionary of all tests found
uuid_table = {}

debug = os.getenv("DEBUG")
hits_so_far = 0
skipped = 0
index_time_query = compute_query()
res = es.search(index=index_name, scroll="60s", size=1000, body=index_time_query)
result_count = res["hits"]["total"]["value"]
if debug:
    print("Got %d Hits:" % result_count)
scroll_id = res["_scroll_id"]
while len(res["hits"]["hits"]) > 0:
    if debug:
        print("")
        print("scroll id %s" % scroll_id)
    hit_list = res["hits"]["hits"]
    hits_so_far += len(hit_list)
    if debug:
        sys.stdout.write("%d " % hits_so_far)
    sys.stdout.flush()
    for hit in hit_list:
        mydoc = hit["_source"]
        uuid = mydoc["uuid"]
        cluster_name = mydoc["cluster_name"]
        user = mydoc["user"]
        try:
            timestamp_field_value = mydoc[timestamp_fieldname]
        except KeyError:
            # hack to work around change in schema for fio results
            # since this is in seconds, convert to millisec expected below
            timestamp_field_value = mydoc["end_time"] * 1000.0
        try:
            timestamp = datetime.strptime(timestamp_field_value, datetime_format)
        except TypeError:
            timestamp_float_sec = timestamp_field_value / 1000.0
            timestamp = datetime.fromtimestamp(timestamp_float_sec, tz=timezone.utc)
        try:
            update = False
            (start_time, end_time, found_cname, found_user) = uuid_table[uuid]
            assert cluster_name == found_cname
            assert user == found_user
            if start_time > timestamp:
                start_time = timestamp
                update = True
            if end_time < timestamp:
                end_time = timestamp
                update = True
            if update:
                uuid_table[uuid] = (start_time, end_time, found_cname, found_user)
        except KeyError:
            start_time = timestamp
            end_time = timestamp
            uuid_table[uuid] = (start_time, end_time, cluster_name, user)

    res = es.scroll(scroll_id=scroll_id, scroll="60s")
print("")
print("")

# print out uuid time range

unsorted_list = []
for u in uuid_table.keys():
    (start_time, end_time, found_cname, found_user) = uuid_table[u]
    unsorted_list.append((start_time, end_time, u, found_cname, found_user))


def extract_timestamp(tpl):
    (start_time, _, _, _, _) = tpl
    return start_time


sorted_list = sorted(unsorted_list, key=extract_timestamp)
for el in sorted_list:
    (start_time, end_time, u, found_cname, found_user) = el
    print("[ {}, {} ] {} {} {}".format(start_time, end_time, u, found_cname, found_user))

if skipped > 0:
    print("skipped %d out of %d results" % (skipped, result_count))
