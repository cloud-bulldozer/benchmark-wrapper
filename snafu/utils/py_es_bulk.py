"""
Opinionated methods for interfacing with Elasticsearch. We provide two
such opinions for creating templates (put_template()) and bulk indexing
(streaming_bulk).
"""

import json
import logging
import math
import time
from collections import Counter, deque
from random import SystemRandom

from elasticsearch import VERSION as es_VERSION
from elasticsearch import exceptions as es_excs
from elasticsearch import helpers

_es_logger = "elasticsearch"

logger = logging.getLogger("snafu")
logger.debug("elasticsearch module version: %d.%d.%d" % es_VERSION)
# Use the random number generator provided by the host OS to calculate our
# random backoff.
_r = SystemRandom()
# The maximum amount of time (in seconds) we'll wait before retrying an
# operation.
_MAX_SLEEP_TIME = 120
# Always use "create" operations, as we also ensure each JSON document being
# indexed has an "_id" field, so we can tell when we are indexing duplicate
# data.
_op_type = "create"
# 100,000 minute timeout talking to Elasticsearch; basically we just don't
# want to timeout waiting for Elasticsearch and then have to retry, as that
# can add undue burden to the Elasticsearch cluster.

_request_timeout = 100000 * 60.0


def _tstos(ts=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S-%Z", time.gmtime(ts))


def _calc_backoff_sleep(backoff):
    b = math.pow(2, backoff)
    return _r.uniform(0, min(b, _MAX_SLEEP_TIME))


def quiet_loggers():
    """
    A convenience function to quiet the urllib3 and elasticsearch1 loggers.
    """
    logging.getLogger("urllib3").setLevel(logging.FATAL)
    logging.getLogger(_es_logger).setLevel(logging.FATAL)


def put_template(es, name, body):
    """
    put_template(es, name, body)
    Arguments:
        es - An Elasticsearch client object already constructed
        name - The name of the template to use
        body - The payload body of the template
    Returns:
        A tuple with the start and end times of the PUT operation, along
        with the number of times the operation was retried.
        Failure modes are raised as exceptions.
    """
    retry = True
    retry_count = 0
    backoff = 1
    beg, end = time.time(), None
    while retry:
        try:
            es.indices.put_template(name=name, body=body)
        except es_excs.ConnectionError as exc:
            # We retry all connection errors
            logger.warn(exc)
            time.sleep(_calc_backoff_sleep(backoff))
            backoff += 1
            retry_count += 1
        except es_excs.TransportError as exc:
            # Only retry on certain 500 errors
            if exc.status_code not in [500, 503, 504]:
                raise
            time.sleep(_calc_backoff_sleep(backoff))
            backoff += 1
            retry_count += 1
        else:
            retry = False
    end = time.time()
    return beg, end, retry_count


def streaming_bulk(es, actions, parallel=False):
    """
    streaming_bulk(es, actions)
    Arguments:
        es - An Elasticsearch client object already constructed
        actions - An iterable for the documents to be indexed
    Returns:
        A tuple with the start and end times, the # of successfully indexed,
        duplicate, and failed documents, along with number of times a bulk
        request was retried.
    """

    # These need to be defined before the closure below. These work because
    # a closure remembers the binding of a name to an object. If integer
    # objects were used, the name would be bound to that integer value only
    # so for the retries, incrementing the integer would change the outer
    # scope's view of the name.  By using a Counter object, the name to
    # object binding is maintained, but the object contents are changed.
    actions_deque = deque()
    actions_retry_deque = deque()
    retries_tracker = Counter()

    def actions_tracking_closure(cl_actions):
        for cl_action in cl_actions:
            assert "_id" in cl_action
            assert "_index" in cl_action
            assert _op_type == cl_action["_op_type"]

            actions_deque.append((0, cl_action))  # Append to the right side ...
            yield cl_action
            # if after yielding an action some actions appear on the retry deque
            # start yielding those actions until we drain the retry queue.
            backoff = 1
            while len(actions_retry_deque) > 0:
                time.sleep(_calc_backoff_sleep(backoff))
                retries_tracker["retries"] += 1
                retry_actions = []
                # First drain, the retry deque entirely so that we know when we
                # have cycled through the entire list to be retried.
                while len(actions_retry_deque) > 0:
                    retry_actions.append(actions_retry_deque.popleft())
                for retry_count, retry_action in retry_actions:
                    actions_deque.append((retry_count, retry_action))  # Append to the right side ...

                    yield retry_action
                # if after yielding all the actions to be retried, some show up
                # on the retry deque again, we extend our sleep backoff to avoid
                # pounding on the ES instance.
                backoff += 1

    beg, end = time.time(), None
    successes = 0
    duplicates = 0
    failures = 0

    # Create the generator that closes over the external generator, "actions"
    generator = actions_tracking_closure(actions)

    if parallel:
        logger.info("Using parallel bulk indexer")
        streaming_bulk_generator = helpers.parallel_bulk(
            es,
            generator,
            chunk_size=10000000,
            max_chunk_bytes=104857600,
            thread_count=8,
            queue_size=4,
            raise_on_error=False,
            raise_on_exception=False,
            request_timeout=_request_timeout,
        )
    else:
        logger.info("Using streaming bulk indexer")
        streaming_bulk_generator = helpers.streaming_bulk(
            es, generator, raise_on_error=False, raise_on_exception=False, request_timeout=_request_timeout
        )

    for ok, resp_payload in streaming_bulk_generator:
        retry_count, action = actions_deque.popleft()
        try:
            resp = resp_payload[_op_type]
            status = resp["status"]
        except KeyError as e:
            logger.error(e)
            assert not ok
            # resp is not of expected form
            logger.warn(resp)

            status = 999
        else:
            assert action["_id"] == resp["_id"]
        if ok:
            successes += 1
        else:
            if status == 409:
                if retry_count == 0:
                    # Only count duplicates if the retry count is 0 ...
                    duplicates += 1
                else:
                    # ... otherwise consider it successful.
                    successes += 1
            elif status == 400:
                doc = {
                    "action": action,
                    "ok": ok,
                    "resp": resp,
                    "retry_count": retry_count,
                    "timestamp": _tstos(time.time()),
                }
                jsonstr = json.dumps(doc, indent=4, sort_keys=True, default=str)
                print(jsonstr)
                # errorsfp.flush()
                failures += 1
            else:
                # Retry all other errors
                print(resp)
                actions_retry_deque.append((retry_count + 1, action))

    end = time.time()

    assert len(actions_deque) == 0
    assert len(actions_retry_deque) == 0

    return (beg, end, successes, duplicates, failures, retries_tracker["retries"])
