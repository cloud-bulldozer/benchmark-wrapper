#!/usr/bin/env python
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import datetime
import hashlib
import json
import logging

# This wrapper assumes the following in fiojob
# per_job_logs=true
#
import os
import ssl
import sys
import time
from distutils.util import strtobool

import configargparse
import elasticsearch
import urllib3

from snafu import benchmarks
from snafu.utils.common_logging import setup_loggers
from snafu.utils.get_prometheus_data import get_prometheus_data
from snafu.utils.py_es_bulk import streaming_bulk
from snafu.utils.request_cache_drop import drop_cache
from snafu.utils.wrapper_factory import wrapper_factory

logger = logging.getLogger("snafu")

# mute elasticsearch and urllib3 logging
es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)


def main():
    # collect arguments
    parser = configargparse.get_argument_parser(
        description="Run benchmark-wrapper and export results.",
        add_config_file_help=True,
        add_env_var_help=True,
        default_config_files=["./snafu.yml"],
        ignore_unknown_config_file_keys=False,
        add_help=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
        help="enables verbose wrapper debugging info",
    )
    parser.add_argument("--config", help="Config file to load", is_config_file=True)
    parser.add_argument("-t", "--tool", help="Provide tool name", required=True)
    parser.add_argument("--run-id", help="Run ID to unify benchmark results in ES", nargs="?", default="NA")
    parser.add_argument("--archive-file", help="Archive file that will be indexed into ES")
    parser.add_argument(
        "--create-archive",
        action="store_const",
        dest="createarchive",
        const=True,
        default=False,
        help="enables creation of archive file",
    )
    index_args, unknown = parser.parse_known_args()
    index_args.index_results = False
    index_args.prefix = "snafu-%s" % index_args.tool

    setup_loggers("snafu", index_args.loglevel)
    log_level_str = "DEBUG" if index_args.loglevel == logging.DEBUG else "INFO"
    logger.info("logging level is %s" % log_level_str)

    # Log loaded benchmarks
    show_db_tb = index_args.loglevel == logging.DEBUG
    benchmarks.DETECTED_BENCHMARKS.log(logger=logger, level=logging.INFO, show_tb=show_db_tb)

    # set up a standard format for time
    FMT = "%Y-%m-%dT%H:%M:%SGMT"

    # instantiate elasticsearch instance and check connection
    es_settings = {}
    es_settings["server"] = os.getenv("es")
    es_settings["verify_cert"] = os.getenv("es_verify_cert", "true").lower()
    if es_settings["server"] and ":443" in es_settings["server"]:
        es_settings["verify_cert"] = "false"
    if es_settings["server"]:
        index_args.prefix = os.getenv("es_index", index_args.prefix)
        logger.info("Using elasticsearch server with host: %s" % es_settings["server"])
        logger.info("Using index prefix for ES: %s" % index_args.prefix)
        index_args.index_results = True
        try:
            if es_settings["verify_cert"] == "false":
                logger.info("Turning off TLS certificate verification")
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
                es = elasticsearch.Elasticsearch(
                    [es_settings["server"]], send_get_body_as="POST", ssl_context=ssl_ctx, use_ssl=False
                )
            else:
                es = elasticsearch.Elasticsearch([es_settings["server"]], send_get_body_as="POST")
            logger.info("Connected to the elasticsearch cluster with info as follows:")
            logger.info(json.dumps(es.info(), indent=4))
        except Exception as e:
            error_msg = "Elasticsearch connection caused an exception: %s" % e

            # Error out if user is only indexing an archive file
            if "archive" in index_args.tool:
                logger.error(error_msg)
                exit(1)
            else:
                logger.warn(error_msg)
                index_args.index_results = False

    index_args.document_size_capacity_bytes = 0
    # call py es bulk using a process generator to feed it ES documents
    if index_args.index_results:
        parallel_setting = strtobool(os.environ.get("parallel", "false"))

        if "archive" in index_args.tool:
            if index_args.archive_file:
                #  if processing a archive file use the process archive file function

                try:
                    res_beg, res_end, res_suc, res_dup, res_fail, res_retry = streaming_bulk(
                        es, process_archive_file(index_args), parallel_setting
                    )
                except Exception as e:
                    logger.error("Attempted to index archive causd an exception: %s" % e)
                    exit(1)
            else:
                logger.error(
                    "Attempted to index archive without specifying a file, use --archive-file=<file>"
                )
                exit(1)
        else:
            # else run a test and process new result documents
            res_beg, res_end, res_suc, res_dup, res_fail, res_retry = streaming_bulk(
                es, process_generator(index_args, parser), parallel_setting
            )

        logger.info(
            "Indexed results - %s success, %s duplicates, %s failures, with %s retries."
            % (res_suc, res_dup, res_fail, res_retry)
        )

        start_t = time.strftime("%Y-%m-%dT%H:%M:%SGMT", time.gmtime(res_beg))
        end_t = time.strftime("%Y-%m-%dT%H:%M:%SGMT", time.gmtime(res_end))

    else:
        logger.info("Not connected to Elasticsearch")
        start_t = time.strftime("%Y-%m-%dT%H:%M:%SGMT", time.gmtime())
        # need to loop through generator and pass on all yields
        # this will execute all jobs without elasticsearch
        if "archive" in index_args.tool:
            if index_args.archive_file:
                logger.info("Processing archive file, but not indexing results...")
                for es_friendly_doc in process_archive_file(index_args):
                    pass
            else:
                logger.error(
                    "Attempted to index archive without specifying a file, use --archive-file=<file>"
                )
                exit(1)
        else:
            for i in process_generator(index_args, parser):
                pass
        end_t = time.strftime("%Y-%m-%dT%H:%M:%SGMT", time.gmtime())

    start_t = datetime.datetime.strptime(start_t, FMT)
    end_t = datetime.datetime.strptime(end_t, FMT)

    # get time delta for indexing run
    tdelta = end_t - start_t
    total_capacity_bytes = index_args.document_size_capacity_bytes
    logger.info(f"Duration of execution - {tdelta}, with total size of {total_capacity_bytes} bytes")


def process_generator(index_args, parser):
    benchmark_wrapper_object_generator = generate_wrapper_object(index_args, parser)

    for wrapper_object in benchmark_wrapper_object_generator:
        if isinstance(wrapper_object, benchmarks.Benchmark):
            for result in wrapper_object.run():
                if result.tag == "get_prometheus_trigger" and "prom_es" in os.environ:
                    index_prom_data(index_args, result.to_json())
                else:
                    es_valid_document = get_valid_es_document(result.to_jsonable(), result.tag, index_args)
                    yield es_valid_document
        else:
            for data_object in wrapper_object.run():
                # drop cache after every sample
                drop_cache()
                for action, index in data_object.emit_actions():
                    if "get_prometheus_trigger" in index and "prom_es" in os.environ:
                        # Action will contain the following
                        """
                        action: {
                                  "uuid": <uuid>
                                  "user": <user>
                                  "clustername": <clustername>
                                  "sample": <int>
                                  "starttime": <datetime> datetime.utcnow().strftime('%s')
                                  "endtime": <datetime>
                                  test_config: {...}
                                }
                        """

                        index_prom_data(index_args, action)
                    else:
                        es_valid_document = get_valid_es_document(action, index, index_args)
                        yield es_valid_document


def generate_wrapper_object(index_args, parser):
    benchmark_wrapper_object = wrapper_factory(index_args.tool, parser)

    yield benchmark_wrapper_object


def get_valid_es_document(action, index, index_args):
    if index != "":
        es_index = index_args.prefix + "-" + index
    else:
        es_index = index_args.prefix
    es_valid_document = {"_index": es_index, "_op_type": "create", "_source": action, "_id": ""}
    logger.debug("Run ID is %s" % {index_args.run_id})
    es_valid_document["run_id"] = action["run_id"] = index_args.run_id
    es_valid_document["_id"] = hashlib.sha256(str(action).encode()).hexdigest()
    document_size_bytes = sys.getsizeof(es_valid_document)
    index_args.document_size_capacity_bytes += document_size_bytes
    logger.debug("document size is: %s" % document_size_bytes)
    logger.debug(json.dumps(es_valid_document, indent=4, default=str))

    if index_args.createarchive:
        write_to_archive_file(index_args, es_valid_document)
    return es_valid_document


def index_prom_data(index_args, action):
    es_settings = {}

    # definition of prometheus data getter, will yield back prom doc
    def get_prometheus_generator(index_args, action):
        prometheus_doc_generator = get_prometheus_data(action)
        for prometheus_doc in prometheus_doc_generator.get_all_metrics():
            es_valid_document = get_valid_es_document(prometheus_doc, "prometheus_data", index_args)
            yield es_valid_document

    es_settings["server"] = os.getenv("prom_es")
    es_settings["verify_cert"] = os.getenv("es_verify_cert", "true")
    if ":443" in es_settings["server"]:
        es_settings["verify_cert"] = "false"
    if es_settings["server"]:
        index_args.prefix = os.getenv("es_index", "")
        logger.info("Using Prometheus elasticsearch server with host: %s" % es_settings["server"])
        logger.info("Using index prefix for prometheus ES: %s" % index_args.prefix)
        index_args.index_results = True
        try:
            if es_settings["verify_cert"] == "false":
                logger.info("Turning off TLS certificate verification for Prometheus ES indexer")
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
                es = elasticsearch.Elasticsearch(
                    [es_settings["server"]], send_get_body_as="POST", ssl_context=ssl_ctx, use_ssl=True
                )
            else:
                es = elasticsearch.Elasticsearch([es_settings["server"]], send_get_body_as="POST")
            logger.info("Connected to the elasticsearch cluster with info as follows:")
            logger.info(json.dumps(es.info(), indent=4))
        except Exception as e:
            logger.warn("Elasticsearch connection caused an exception: %s" % e)
            index_args.index_results = False

    # check that we want to index and that the prom_es exist.
    if index_args.index_results:
        logger.info("initializing prometheus indexing")
        parallel_setting = strtobool(os.environ.get("parallel", "false"))
        res_beg, res_end, res_suc, res_dup, res_fail, res_retry = streaming_bulk(
            es, get_prometheus_generator(index_args, action), parallel_setting
        )

        logger.info(
            "Prometheus indexed results - %s success, %s duplicates, %s failures, with %s retries."
            % (res_suc, res_dup, res_fail, res_retry)
        )
        start_t = time.strftime("%Y-%m-%dT%H:%M:%SGMT", time.gmtime(res_beg))
        end_t = time.strftime("%Y-%m-%dT%H:%M:%SGMT", time.gmtime(res_end))
        # set up a standard format for time
        FMT = "%Y-%m-%dT%H:%M:%SGMT"
        start_t = datetime.datetime.strptime(start_t, FMT)
        end_t = datetime.datetime.strptime(end_t, FMT)

        # get time delta for indexing run
        tdelta = end_t - start_t
        logger.info("Prometheus indexing duration of execution - %s" % tdelta)


def process_archive_file(index_args):

    if os.path.isfile(index_args.archive_file):
        with open(index_args.archive_file) as f:
            for line in f:
                es_friendly_document = json.loads(line)
                document_size_bytes = sys.getsizeof(es_friendly_document)
                index_args.document_size_capacity_bytes += document_size_bytes
                yield es_friendly_document
    else:
        logger.error("%s Not found" % index_args.archive_file)
        exit(1)


def write_to_archive_file(index_args, es_friendly_documment):

    if index_args.archive_file:
        archive_filename = index_args.archive_file
    else:
        #  assumes that all documents have the same structure
        user = es_friendly_documment["_source"]["user"]
        clustername = es_friendly_documment["_source"]["clustername"]
        uuid = es_friendly_documment["_source"]["uuid"]
        #  create archive file as user_clustername_uuid.archive in cwd
        archive_filename = user + "_" + clustername + "_" + uuid + ".archive"

    #  Will write each es friendly document on 1 line, this makes re-indexing easier later
    with open(archive_filename, "a") as f:
        json.dump(es_friendly_documment, f)
        f.write(os.linesep)


if __name__ == "__main__":
    sys.exit(main())
