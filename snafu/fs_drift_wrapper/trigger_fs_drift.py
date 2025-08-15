import json
import os
import re
import socket
import subprocess
import time

from snafu.vfs_stat import get_vfs_stat_dict

regex = r"counters.([0-9]{2}).[0-9,\.,\-,a-z,A-Z]*.json"
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
        self.network_shared_dir = os.path.join(self.working_dir, "network-shared")
        self.result_dir = result_dir
        self.json_output_file = os.path.join(self.result_dir, "fs-drift.json")
        self.user = user
        self.uuid = uuid
        self.sample = sample
        self.cluster_name = cluster_name
        # for K8S this is really a pod ID, not a host
        self.host = socket.gethostname()

    def ensure_dir_exists(self, directory):
        if not os.path.exists(directory):
            os.mkdir(directory)

    def emit_actions(self):
        """
        Executes test and calls document parsers, if index_data is true will yield normalized data
        """

        self.ensure_dir_exists(self.working_dir)

        # clear out any unconsumed response time files or thread counters in this directory
        if os.path.exists(self.network_shared_dir):
            contents = os.listdir(self.network_shared_dir)
            for c in contents:
                if c.endswith(".csv"):
                    os.unlink(os.path.join(self.network_shared_dir, c))
                elif c.startswith("counters"):
                    os.unlink(os.path.join(self.network_shared_dir, c))

        cmd = [
            "fs-drift.py",
            "--top",
            self.working_dir,
            "--output-json",
            self.json_output_file,
            "--response-times",
            "Y",
            "--input-yaml",
            self.yaml_input_file,
        ]
        self.logger.info("running:" + " ".join(cmd))
        self.logger.info("from current directory %s" % os.getcwd())
        try:
            subprocess.check_call(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.logger.exception(e)
            raise FsDriftWrapperException("fs-drift.py non-zero process return code %d" % e.returncode)
        self.logger.info(f"completed sample {self.sample} , results in {self.json_output_file}")

        fsdict = get_vfs_stat_dict(self.working_dir)
        with open(self.json_output_file) as f:
            data = json.load(f)
        yield from self.process_result(data, fsdict)
        elapsed_time = float(data["results"]["elapsed"])
        start_time = data["results"]["start-time"]
        self.logger.info("elapsed time = %f start_time = %d" % (elapsed_time, start_time))
        yield from self.process_rsptimes(start_time, elapsed_time)
        yield from self.process_per_thread_counters(start_time)

    def process_result(self, data, filesys):
        params = data["parameters"]
        timestamp = data["results"]["date"]
        threads = data["results"]["in-thread"]
        for tid in threads.keys():
            thrd = threads[tid]
            thrd["fsdict"] = filesys
            thrd["date"] = timestamp
            thrd["thr-id"] = tid
            thrd["host"] = self.host
            thrd["sample"] = self.sample
            thrd["cluster_name"] = self.cluster_name
            thrd["uuid"] = self.uuid
            thrd["user"] = self.user
            thrd["params"] = params
            yield thrd, "results"

    def process_rsptimes(self, start_time, elapsed_time):
        """
        convert response time logs to stats as a function of time
        """
        rsptime_file = os.path.join(self.network_shared_dir, "stats-rsptimes.csv")
        sampling_interval = max(int(elapsed_time / 120.0), 1)
        self.logger.info("sampling_interval %d" % sampling_interval)
        if sampling_interval <= 1:
            self.logger.info("not enough duration to calculate response time stats, skipping")
            return
        cmd = ["rsptime_stats.py", "--time-interval", str(sampling_interval), self.network_shared_dir]
        self.logger.info("process response times with: %s" % " ".join(cmd))
        try:
            process = subprocess.check_call(cmd, stderr=subprocess.STDOUT)  # noqa
        except subprocess.CalledProcessError as e:
            self.logger.exception(e)
            raise FsDriftWrapperException("rsptime_stats failed, see exception in log")
        self.logger.info(f"response time result {rsptime_file}")
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
                    interval["host"] = self.host
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

    def process_per_thread_counters(self, start_time):
        """
        reads in JSON per-thread counters, converts counters to rates
        """

        counter_dir = os.path.join(self.working_dir, "network-shared")
        for fn in os.listdir(counter_dir):
            previous_obj = None
            if fn.startswith("counters") and fn.endswith("json"):
                pathnm = os.path.join(counter_dir, fn)
                matched = counters_regex_prog.match(fn)
                thread_id = matched.group(1)
                with open(pathnm) as f:
                    thread_counters = json.load(f)
                self.logger.info(
                    "process %d intervals from rates-over-time file %s " % (len(thread_counters), fn)
                )
                for snapshot in thread_counters:

                    # compute timestamp from start of test and time since start

                    time_since_test_start = float(snapshot["elapsed-time"])
                    counter_time = time_since_test_start + start_time
                    timestamp_str = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(counter_time))

                    # convert counters into rates

                    rate_obj = self.compute_rates(snapshot, previous_obj)
                    previous_obj = snapshot

                    # add fields for elastic search indexing

                    rate_obj["date"] = timestamp_str
                    rate_obj["thread"] = thread_id
                    rate_obj["host"] = self.host
                    rate_obj["uuid"] = self.uuid
                    rate_obj["timestamp"] = timestamp_str
                    rate_obj["cluster_name"] = self.cluster_name
                    rate_obj["user"] = self.user
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
