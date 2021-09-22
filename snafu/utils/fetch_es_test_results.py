# common code to fetch Elasticsearch benchmark-operator test results
# for analysis by benchmark-specific scripts
# NOTE: at present you must set environment variable
# PYTHONPATH=your-benchmark-wrapper-clone-directory
# so that the import statement "import snafu.utils.fetch_es_test_wrapper" works
# I don't like that but not sure why.

import os
#for debugging:
#import sys
from datetime import datetime, timezone
from elasticsearch import Elasticsearch

es_dev_server = "https://search-perfscale-dev-chmf5l4sh66lvxbnadi4bznl3a.us-west-2.es.amazonaws.com"


class SnafuResultException(Exception):
    pass


# get an ES
def connect_es():
    cert_verify = False if os.getenv("ES_NO_VERIFY_CERT") else True
    es_url = os.getenv("ES_SERVER", default=es_dev_server)
    print("Elasticsearch server at {}, verify_certs {}".format(es_url, str(cert_verify)))
    es = Elasticsearch([es_url], verify_certs=cert_verify)
    return es


# next_result returns a generator object that yields ES documents for the specified uuid
# the benchmark analysis tool does not need to understand how elasticsearch returns documents
# this is similar to design of wrappers -- benchmark does not need to understand how
# test results make it into elasticsearch


def result_generator_for_uuid(es_obj, index_pattern, uuid):
    debug = os.getenv("DEBUG")
    # only return test results with this uuid
    uuid_query = {
        "query": {"simple_query_string": {"query": uuid, "fields": ["uuid"], "default_operator": "and"}}
    }
    res = es_obj.search(index=index_pattern, scroll="60s", size=1000, body=uuid_query)
    if debug:
        print("Got %d Hits:" % res["hits"]["total"]["value"])
    scroll_id = res["_scroll_id"]
    wrong_uuid = 0

    while len(res["hits"]["hits"]) > 0:
        if debug:
            print("")
            print("scroll id %s" % scroll_id)
            print("got %d hits this time" % len(res["hits"]["hits"]))
        for hit in res["hits"]["hits"]:
            src = hit["_source"]

            # maybe I'm paranoid ;-)
            uuid_found = src["uuid"]
            if uuid_found != uuid:
                raise SnafuResultException(
                    "elastic search returned result with uuid {} instead of {}".format(uuid_found, uuid)
                )
                wrong_uuid += 1
                continue

            yield hit

        # get the next batch of documents
        res = es_obj.scroll(scroll_id=scroll_id, scroll="60s")

    if wrong_uuid > 0:
        print("WARNING: %d results did not have matching uuid %s" % (wrong_uuid, uuid))


# function to construct ES query to fetch all UUIDs in a time range 

def compute_query_for_uuids(starting_time_in, ending_time_in):
    match_all = {"size": 100, "query": {"match_all": {}}}
    query_times = match_all
    if starting_time_in:
        starting_time_str = starting_time_in
        ending_time_str = "now"
        if ending_time_in:
            ending_time_str = ending_time_in
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


# function to fetch all UUIDs for a time range
# parameters:
#   es - elasticsearch client object (from connect_es above)
#   index_name - really index pattern name
#   timestamp_fieldname - field name in document containing timestamp
#   starting_time_in - can be None only if ending_time_in is None
#   ending_time_in - can be None, defaults to "now"
#
# note: if start_time is None, then entire index is searched
# time format is given by datetime_format below
#
# uuids are returned as a dictionary of tuples indexed by uuid, 
# tuple fields are:
#    start_time - timestamp of oldest result for that uuid
#    end_time - timestamp of newest result for that uuid
#    cluster_name - the "cluster_name" field used in the benchmark CR
#    user - the "user" field used in the benchmark CR
#

def get_uuid_tuples(es, index_name, timestamp_fieldname, starting_time_in, ending_time_in):
    # dictionary of all tests found
    uuid_table_out = {}
    # used by strptime()
    datetime_format = "%Y-%m-%dT%H:%M:%S.%f%z"
    debug = os.getenv("DEBUG")
    hits_so_far = 0
    index_time_query = compute_query_for_uuids(starting_time_in, ending_time_in)
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
        #if debug:
            #sys.stdout.write("%d " % hits_so_far)
            #sys.stdout.flush()
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
                (start_time, end_time, found_cname, found_user) = uuid_table_out[uuid]
                assert cluster_name == found_cname
                assert user == found_user
                if start_time > timestamp:
                    start_time = timestamp
                    update = True
                if end_time < timestamp:
                    end_time = timestamp
                    update = True
                if update:
                    uuid_table_out[uuid] = (start_time, end_time, found_cname, found_user)
            except KeyError:
                start_time = timestamp
                end_time = timestamp
                uuid_table_out[uuid] = (start_time, end_time, cluster_name, user)

        res = es.scroll(scroll_id=scroll_id, scroll="60s")
    return uuid_table_out

