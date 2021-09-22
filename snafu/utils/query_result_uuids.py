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

from snafu.utils.fetch_es_test_results import connect_es, get_uuid_tuples

NOTOK = 1


def usage(errmsg):
    print("ERROR: %s" % errmsg)
    print("usage: query_test_uuids.py results-index-name timestamp-fieldname [ start-time [ end-time ]]")
    sys.exit(NOTOK)


def extract_timestamp(tpl):
    (start_time, _, _, _, _) = tpl
    return start_time


if len(argv) < 3:
    usage("too few command line parameters")

index_name = argv[1]
timestamp_fieldname = argv[2]
starting_time_in = None
ending_time_in = None
if len(argv) > 3:
    starting_time_in = argv[3]
if len(argv) > 4:
    ending_time_in = argv[4]

es = connect_es()

uuid_table = get_uuid_tuples(es, index_name, timestamp_fieldname, starting_time_in, ending_time_in)

# sort uuids by start_time of results for that uuid

unsorted_list = []
for u in uuid_table.keys():
    (start_time, end_time, found_cname, found_user) = uuid_table[u]
    unsorted_list.append((start_time, end_time, u, found_cname, found_user))
sorted_list = sorted(unsorted_list, key=extract_timestamp)

# print them in CSV format

print("")
print("")
for el in sorted_list:
    (start_time, end_time, u, found_cname, found_user) = el
    print("[ {}, {} ] {} {} {}".format(start_time, end_time, u, found_cname, found_user))
