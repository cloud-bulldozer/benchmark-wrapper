import json
import logging
import os
import time
from datetime import datetime

import urllib3
from prometheus_api_client import PrometheusConnect

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("snafu")


class get_prometheus_data:
    def __init__(self, action):

        self.sample_info_dict = action
        self.uuid = action["uuid"]
        self.user = action["user"]
        self.cluster_name = action["cluster_name"]
        self.test_config = action["test_config"]

        # change datetime in seconds string to datetime object
        starttime = datetime.fromtimestamp(int(self.sample_info_dict["starttime"]))
        self.start = starttime

        # change datetime in seconds string to datetime object
        endtime = datetime.fromtimestamp(int(self.sample_info_dict["endtime"]))
        self.end = endtime

        # step value to be used in prometheus query
        # default is 30 seconds(openshift default scraping interval)
        # but can be overridden with env
        if "prom_step" in os.environ:
            self.T_Delta = os.environ["prom_step"]
        else:
            self.T_Delta = 30

        self.get_data = False
        if "prom_token" in os.environ and "prom_url" in os.environ:
            self.get_data = True
            token = os.environ["prom_token"]
            self.url = os.environ["prom_url"]
            bearer = "Bearer " + token
            self.headers = {"Authorization": bearer}
            self.pc = PrometheusConnect(url=self.url, headers=self.headers, disable_ssl=True)
        else:
            logger.warn(
                """snafu service account token and prometheus url not set \n
                        No Prometheus data will be indexed"""
            )

    def get_all_metrics(self):

        # check get_data bool, if false by-pass all processing
        if self.get_data:
            start_time = time.time()

            # resolve directory  the tool include file
            dirname = os.path.dirname(os.path.realpath(__file__))
            include_file_dir = os.path.join(dirname, "prometheus_labels/")
            tool_include_file = include_file_dir + self.sample_info_dict["tool"] + "_included_labels.json"

            # check if tools include file is there
            # if not use the default include file
            if os.path.isfile(tool_include_file):
                filename = tool_include_file
            else:
                filename = os.path.join(include_file_dir, "included_labels.json")
            logger.info("using prometheus metric include file %s" % filename)

            # open tools include file and loop through all
            with open(filename) as f:
                datastore = json.load(f)

            for metric_name in datastore["data"]:

                query_item = datastore["data"][metric_name]
                query = query_item["query"]
                label = query_item["label"]

                step = str(self.T_Delta) + "s"
                try:
                    # Execute custom query to pull the desired labels between X and Y time.
                    response = self.pc.custom_query_range(query, self.start, self.end, step, None)

                except Exception as e:
                    # response undefined at this point, we want to skip next for loop
                    response = []
                    logger.info(query)
                    logger.warn("failure to get metric results %s" % e)

                for result in response:
                    # clean up name key from __name__ to name
                    result["metric"]["name"] = ""
                    if "__name__" in result["metric"]:
                        result["metric"]["name"] = result["metric"]["__name__"]
                        del result["metric"]["__name__"]
                    else:
                        result["metric"]["name"] = label
                    # each result has a list, we must flatten it out in order to send to ES
                    for value in result["values"]:
                        # fist index is time stamp
                        timestamp = datetime.utcfromtimestamp(value[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                        # second index is value of metric
                        if "NaN" in value[1]:  # need to handle values that are NaN, Inf, or -Inf
                            metric_value = 0
                        else:
                            metric_value = float(value[1])

                        flat_doc = {
                            "metric": result["metric"],
                            "Date": timestamp,
                            "value": metric_value,
                            "metric_name": metric_name,
                        }

                        flat_doc.update(self.sample_info_dict)
                        yield flat_doc

            logger.debug("Total Time --- %s seconds ---" % (time.time() - start_time))
