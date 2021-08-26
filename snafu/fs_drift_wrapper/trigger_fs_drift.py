import json
import os
import re
import subprocess
import time

regex = r"counters.([0-9]{2}).[0-9,\.,\-,a-z,A-Z]*.json"  # noqa
counters_regex_prog = re.compile(regex)


class FsDriftWrapperException(Exception):
    pass


class _trigger_fs_drift:
    """
    Will execute with the provided arguments and return normalized results for indexing
    """

    def __init__(self, logger, yaml_input_file, cluster_name, working_dir, result_dir, user, uuid, sample):
        self.logger = logger
        self.yaml_input_file = yaml_input_file
        self.working_dir = working_dir
        self.result_dir = result_dir
        self.user = user
        self.uuid = uuid
        self.sample = sample
        self.cluster_name = cluster_name

    def ensure_dir_exists(self, directory):
        if not os.path.exists(directory):
            os.mkdir(directory)

    def emit_actions(self):
        """
        Executes test and calls document parsers, if index_data is true will yield normalized data
        """

        self.ensure_dir_exists(self.working_dir)
        rsptime_dir = os.path.join(self.working_dir, "network-shared")

        # clear out any unconsumed response time files in this directory
        if os.path.exists(rsptime_dir):
            contents = os.listdir(rsptime_dir)
            for c in contents:
                if c.endswith(".csv"):
                    os.unlink(os.path.join(rsptime_dir, c))

        json_output_file = os.path.join(self.result_dir, "fs-drift.json")
        network_shared_dir = os.path.join(self.working_dir, "network-shared")
        rsptime_file = os.path.join(network_shared_dir, "stats-rsptimes.csv")
        cmd = [
            "fs-drift.py",
            "--top",
            self.working_dir,
            "--output-json",
            json_output_file,
            "--response-times",
            "Y",
            "--input-yaml",
            self.yaml_input_file,
        ]
        self.logger.info("running:" + " ".join(cmd))
        self.logger.info("from current directory %s" % os.getcwd())
        try:
            process = subprocess.check_call(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.logger.exception(e)
            raise FsDriftWrapperException("fs-drift.py non-zero process return code %d" % e.returncode)
        self.logger.info("completed sample {} , results in {}".format(self.sample, json_output_file))
        with open(json_output_file) as f:
            data = json.load(f)
            params = data["parameters"]
            timestamp = data["results"]["date"]
            threads = data["results"]["in-thread"]
            for tid in threads.keys():
                thrd = threads[tid]
                thrd["date"] = timestamp
                thrd["thr-id"] = tid
                thrd["sample"] = self.sample
                thrd["cluster_name"] = self.cluster_name
                thrd["uuid"] = self.uuid
                thrd["user"] = self.user
                thrd["params"] = params
                yield thrd, "results"

        # process response time data

        elapsed_time = float(data["results"]["elapsed"])
        start_time = data["results"]["start-time"]
        sampling_interval = max(int(elapsed_time / 120.0), 1)
        cmd = ["rsptime_stats.py", "--time-interval", str(sampling_interval), rsptime_dir]
        self.logger.info("process response times with: %s" % " ".join(cmd))
        try:
            process = subprocess.check_call(cmd, stderr=subprocess.STDOUT)  # noqa
        except subprocess.CalledProcessError as e:
            self.logger.exception(e)
            raise FsDriftWrapperException("rsptime_stats return code %d" % e.returncode)
        self.logger.info("response time result {}".format(rsptime_file))
        with open(rsptime_file) as rf:
            lines = [line.strip() for line in rf.readlines()]
            start_grabbing = False
            for line in lines:
                if line.startswith("time-since-start"):
                    start_grabbing = True
                elif start_grabbing:
                    if line == "":
                        continue
                    flds = line.split(",")
                    rsptime_date = start_time + int(flds[0])
                    rsptime_date_str = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(rsptime_date))
                    interval = {}
                    # number of fs-drift file operations in this interval
                    interval["op-count"] = int(flds[2])
                    if interval["op-count"] == 0:
                        self.logger.info(
                            "no response time data in interval starting at " + rsptime_date_str
                        )  # noqa
                        # no response time data for this interval
                        # FIXME: how do we indicate to grafana that preceding sample
                        # is not continuing into this interval.
                        continue
                    interval["cluster_name"] = self.cluster_name
                    interval["uuid"] = self.uuid
                    interval["user"] = self.user
                    interval["sample"] = self.sample
                    interval["date"] = rsptime_date_str
                    # file operations per second in this interval
                    interval["file-ops-per-sec"] = float(flds[2]) / sampling_interval
                    interval["min"] = float(flds[3])
                    interval["max"] = float(flds[4])
                    interval["mean"] = float(flds[5])
                    interval["50%"] = float(flds[7])
                    interval["90%"] = float(flds[8])
                    interval["95%"] = float(flds[9])
                    interval["99%"] = float(flds[10])
                    yield interval, "rsptimes"

        # process counter data

        for fn in os.listdir(rsptime_dir):
            previous_obj = None
            if fn.startswith("counters") and fn.endswith("json"):
                pathnm = os.path.join(rsptime_dir, fn)
                matched = counters_regex_prog.match(fn)
                thread_id = matched.group(1)
                with open(pathnm, "r") as f:
                    records = [line.strip() for line in f.readlines()]
                json_start = 0
                self.logger.info("process %d records from rates-over-time file %s " % (len(records), fn))
                for index, record in enumerate(records):
                    if record == "{":
                        json_start = index
                    if record == "}{" or record == "}":
                        # extract next JSON string from counter logfile

                        json_str = " ".join(records[json_start:index])
                        json_str += " }"
                        if record == "}{":
                            records[index] = "{"
                        json_start = index
                        json_obj = json.loads(json_str)
                        rate_obj = self.compute_rates(json_obj, previous_obj)
                        previous_obj = json_obj

                        # timestamp this sample

                        time_since_test_start = float(rate_obj["elapsed-time"])
                        counter_time = time_since_test_start + start_time
                        timestamp_str = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(counter_time))
                        rate_obj["date"] = timestamp_str

                        # add other info needed to display data in elastic search

                        rate_obj["thread"] = thread_id
                        rate_obj["cluster_name"] = self.cluster_name
                        rate_obj["user"] = self.user
                        rate_obj["uuid"] = self.uuid
                        rate_obj["sample"] = self.sample
                        yield rate_obj, "rates-over-time"

    # assumes that the input dictionaries have same fields
    # and that all fields other than 'elapsed_time' are integer counters
    # so we can compute rate from them and delta_time
    # if previous sample is None, then this is the first sample
    # so previous sample counter is implicitly zero

    def compute_rates(self, current_sample, previous_sample):
        time_since_test_start = float(current_sample["elapsed-time"])
        if previous_sample is not None:
            previous_time_since_test_start = float(previous_sample["elapsed-time"])
        else:
            previous_time_since_test_start = 0
        delta_time = time_since_test_start - previous_time_since_test_start
        assert delta_time > 0.5
        rate_dict = {}
        for k in current_sample.keys():
            if k != "elapsed-time":
                if previous_sample:
                    rate_dict[k] = (int(current_sample[k]) - int(previous_sample[k])) / delta_time
                else:
                    rate_dict[k] = int(current_sample[k]) / delta_time
            else:
                rate_dict[k] = current_sample[k]
        return rate_dict
