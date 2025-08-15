import json
import os
import socket
import subprocess
import time
from datetime import datetime

from snafu.utils.request_cache_drop import http_timeout
from snafu.utils.sync_pods_with_redis import redis_sync_pods
from snafu.vfs_stat import get_vfs_stat_dict


class SmallfileWrapperException(Exception):
    pass


class _trigger_smallfile:
    """
    execute with provided arguments and return results for indexing
    """

    def __init__(
        self,
        logger,
        operation,
        yaml_input_file,
        cluster_name,
        working_dir,
        result_dir,
        user,
        uuid,
        redis_host,
        redis_timeout,
        redis_timeout_th,
        clients,
        sample,
    ):
        self.logger = logger
        self.operation = operation
        self.yaml_input_file = yaml_input_file
        self.working_dir = working_dir
        self.result_dir = result_dir
        self.user = user
        self.uuid = uuid
        self.sample = sample
        self.cluster_name = cluster_name
        self.redis_host = redis_host
        self.redis_timeout = int(redis_timeout)
        self.redis_timeout_th = int(redis_timeout_th)
        self.clients = int(clients)
        self.host = socket.gethostname()
        self.logger.info(
            (
                "working dir. %s, sample %d, uuid %s, redis_host %s, "
                + "redis_timeout %d, redis_timeout_th %d %%, clients %d"
            )
            % (
                self.working_dir,
                self.sample,
                self.uuid,
                self.redis_host,
                self.redis_timeout,
                self.redis_timeout_th,
                self.clients,
            )
        )

    def ensure_dir_exists(self, directory):
        if not os.path.exists(directory):
            os.mkdir(directory)

    def emit_actions(self):
        """
        Executes test, parse output, yield elastic-ready documents
        """

        self.ensure_dir_exists(self.working_dir)
        rsptime_dir = os.path.join(self.working_dir, "network_shared")

        # clear out any unconsumed response time files in this directory
        if os.path.exists(rsptime_dir):
            contents = os.listdir(rsptime_dir)
            for c in contents:
                if c.endswith(".csv"):
                    os.unlink(os.path.join(rsptime_dir, c))

        if self.clients > 1 and self.redis_host:
            channel = "smallfile-%s-sample-%d-op-%s-before" % (self.uuid, self.sample, self.operation)
            redis_sync_pods(self.clients, 2 * http_timeout, self.redis_host, channel, self.logger)

        # only do 1 operation at a time in emit_actions
        # so that cache dropping works right

        before = datetime.now()
        json_output_file = os.path.join(self.result_dir, "%s.json" % self.operation)
        network_shared_dir = os.path.join(self.working_dir, "network_shared")
        rsptime_file = os.path.join(network_shared_dir, "stats-rsptimes.csv")
        cmd = [
            "smallfile_cli.py",
            "--operation",
            self.operation,
            "--top",
            self.working_dir,
            "--output-json",
            json_output_file,
            "--response-times",
            "Y",
            "--yaml-input-file",
            self.yaml_input_file,
        ]
        self.logger.info("running:" + " ".join(cmd))
        self.logger.info("from current directory %s" % os.getcwd())
        try:
            subprocess.check_call(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.logger.exception(e)
            raise SmallfileWrapperException("smallfile_cli.py non-zero process return code %d" % e.returncode)
        self.logger.info(
            "completed sample {} for operation {} , results in {}".format(
                self.sample, self.operation, json_output_file
            )
        )
        if self.operation == "cleanup":
            return  # skip reporting data

        fsdict = get_vfs_stat_dict(self.working_dir)

        with open(json_output_file) as f:
            data = json.load(f)
            timestamp = data["results"]["date"]
            params = data["params"]
            for tid in data["results"]["thread"].keys():
                thrd = data["results"]["thread"][tid]
                thrd["params"] = params
                thrd["fsinfo"] = fsdict
                thrd["cluster_name"] = self.cluster_name
                thrd["uuid"] = self.uuid
                thrd["user"] = self.user
                thrd["sample"] = self.sample
                thrd["optype"] = self.operation
                thrd["host"] = self.host
                thrd["tid"] = tid
                thrd["date"] = timestamp
                yield thrd, "results"

        # process response time data

        elapsed_time = float(data["results"]["elapsed"])
        start_time = data["results"]["startTime"]
        cmd = [
            "smallfile_rsptimes_stats.py",
            "--time-interval",
            str(max(int(elapsed_time / 120.0), 1)),
            "--start-time",
            str(int(start_time)),
            rsptime_dir,
        ]
        self.logger.info("process response times with: %s" % " ".join(cmd))
        try:
            subprocess.check_call(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.logger.exception(e)
            raise SmallfileWrapperException("rsptime_stats return code %d" % e.returncode)
        self.logger.info(f"response time result for operation {self.operation} in {rsptime_file}")
        with open(rsptime_file) as rf:
            lines = [ln.strip() for ln in rf.readlines()]
            start_grabbing = False
            for line in lines:
                if line.startswith("time-since-start"):
                    start_grabbing = True
                elif start_grabbing:
                    if line == "":
                        continue
                    flds = line.split(",")
                    interval = {}
                    interval["iops"] = int(flds[2])
                    if interval["iops"] > 0.0:
                        rsptime_date = int(flds[0])
                        rsptime_date_str = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(rsptime_date))
                        interval["cluster_name"] = self.cluster_name
                        interval["uuid"] = self.uuid
                        interval["user"] = self.user
                        interval["sample"] = self.sample
                        interval["optype"] = self.operation
                        interval["host"] = self.host
                        interval["date"] = rsptime_date_str
                        interval["min"] = float(flds[3])
                        interval["max"] = float(flds[4])
                        interval["mean"] = float(flds[5])
                        interval["50%"] = float(flds[7])
                        interval["90%"] = float(flds[8])
                        interval["95%"] = float(flds[9])
                        interval["99%"] = float(flds[10])
                        yield interval, "rsptimes"

        if self.clients > 1 and self.redis_host:
            channel = "smallfile-%s-sample-%d-op-%s-after" % (self.uuid, self.sample, self.operation)
            extra_timeout = int((datetime.now() - before).seconds * self.redis_timeout_th / 100)
            redis_timeout = self.redis_timeout + extra_timeout
            redis_sync_pods(self.clients, redis_timeout, self.redis_host, channel, self.logger)
