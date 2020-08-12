import os
import json
import logging
import urllib3
from datetime import datetime, timedelta
import time
import sys
from prometheus_api_client import PrometheusConnect
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("snafu")

class get_prometheus_data():
    def __init__(self, action):

        self.uuid = action["uuid"]
        self.user = action["user"]
        self.cluster_name = action["cluster_name"]
        self.test_config = action["test_config"]

        # change datetime in seconds string to datetime object
        starttime = datetime.fromtimestamp(int(action["starttime"]))
        self.start = starttime.datetime()

        # change datetime in seconds string to datetime object
        endtime = datetime.fromtimestamp(int(action["endtime"]))
        # add 120s buffer to end time
        endtime = endtime + timedelta(seconds=120)
        self.end = endtime.datetime

        # step value to be used in prometheus query
        self.T_Delta = 30

        self.get_data = False
        if "prom_token" in os.environ and "prom_url" in os.environ:
            self.get_data = True
            token = os.environ["prom_token"]
            self.url = os.environ["prom_url"]
            bearer = "Bearer " + token
            self.headers = {'Authorization': bearer}
            self.pc = PrometheusConnect(url=self.url, headers=self.headers, disable_ssl=True)
        else:
            logger.warn("""snafu service account token and prometheus url not set \n
                        No Prometheus data will be indexed""")

    def get_all_metrics(self):

        # check get_data bool, if false by-pass all processing
        if self.get_data:
            start_time = time.time()

            filename = os.path.join(sys.path[0], 'utils/prometheus_labels/included_labels.json')
            with open(filename, 'r') as f:
                datastore = json.load(f)

            # for label in self.get_label_list():
            for label in datastore["data"]:

                # query_start_time = time.time()
                query = "irate(%s[1m])" % label
                """
                If there are additional queries need we should create a list or dict that can be iterated on
                """
                step = str(self.T_Delta) + "s"
                try:
                    # response = self.api_call(query)
                    response = self.pc.custom_query_range(query,
                                                          self.start,
                                                          self.end,
                                                          step,
                                                          None)
                except Exception as e:
                    logger.warn("failure to get metric results %s" % e)

                results = response['result']

                # results is a list of all hits
                """
                    TODO: update with proper parsing of response document
                """

                for result in results:
                    # clean up name key from __name__ to name
                    result["metric"]["name"] = ""
                    result["metric"]["name"] = result["metric"]["__name__"]
                    del result["metric"]["__name__"]
                    # each result has a list, we must flatten it out in order to send to ES
                    for value in result["values"]:
                        # fist index is time stamp
                        timestamp = datetime.utcfromtimestamp(value[0]).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        # second index is value of metric
                        if "NaN" in value[1]:  # need to handle values that are NaN, Inf, or -Inf
                            metric_value = 0
                        else:
                            metric_value = float(value[1])

                        flat_doc = {"uuid": self.uuid,
                                    "user": self.user,
                                    "cluster_name": self.cluster_name,
                                    "metric": result["metric"],
                                    "Date": timestamp,
                                    "value": metric_value,
                                    "test_config": self.test_config
                                    }

                        yield flat_doc
                else:
                    pass
                    # logger.debug("Not exporting data for %s" % label)

            logger.debug("Total Time --- %s seconds ---" % (time.time() - start_time))
