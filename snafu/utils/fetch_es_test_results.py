# common code to fetch Elasticsearch benchmark-operator test results
# for analysis by benchmark-specific scripts

import os

from elasticsearch import Elasticsearch

es_dev_server = "https://search-perfscale-dev-chmf5l4sh66lvxbnadi4bznl3a.us-west-2.es.amazonaws.com"


class SnafuResultException(Exception):
    pass


# get an ES
def connect_es():
    cert_verify = False if os.getenv("ES_NO_VERIFY_CERT") else True
    es_url = os.getenv("ES_SERVER", default=es_dev_server)
    es = Elasticsearch([es_url], verify_certs=cert_verify)
    return es


# fetch_from_index returns a generator object that yields ES documents for the specified uuid
# the benchmark analysis tool does not need to understand how elasticsearch returns documents
# this is similar to design of wrappers -- benchmark does not need to understand how
# test results make it into elasticsearch


def next_result(es_obj, index_pattern, uuid):
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
