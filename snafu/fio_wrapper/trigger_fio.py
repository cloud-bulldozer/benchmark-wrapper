import configparser
import json
import logging
import os
import subprocess
from copy import deepcopy
from datetime import datetime

from .fio_hist_parser import compute_percentiles_from_logs

logger = logging.getLogger("snafu")

_log_files = {
    "bw": {"metric": "bandwidth"},
    "iops": {"metric": "iops"},
    "lat": {"metric": "latency"},
    "clat": {"metric": "latency"},
    "slat": {"metric": "latency"},
}  # ,'clat_hist_processed'
_data_direction = {0: "read", 1: "write", 2: "trim"}


class _trigger_fio:
    """
    Will execute fio with the provided arguments and return normalized results for indexing
    """

    def __init__(
        self,
        fio_jobs,
        cluster_name,
        working_dir,
        fio_jobs_dict,
        host_file,
        user,
        uuid,
        sample,
        fio_analyzer_obj,
        numjob=1,
        process_histogram=False,
    ):
        self.fio_jobs = fio_jobs
        self.working_dir = working_dir
        self.fio_jobs_dict = fio_jobs_dict
        self.host_file = host_file
        self.user = user
        self.uuid = uuid
        self.sample = sample
        self.fio_analyzer_obj = fio_analyzer_obj
        self.numjob = numjob
        self.histogram_process = process_histogram
        self.cluster_name = cluster_name
        self.fio_version = ""
        self.hosts = ""

    def _document_payload(self, data, end_time):  # pod_details,
        processed = []
        fio_starttime = {}
        earliest_starttime = float("inf")
        for result in data["client_stats"]:
            document = {
                "uuid": self.uuid,
                "user": self.user,
                "cluster_name": self.cluster_name,
                "hosts": self.hosts,
                "fio-version": self.fio_version,
                "timestamp_end": int(end_time) * 1000,  # this is in ms
                # "nodeName": pod_details["hostname"],
                "sample": int(self.sample),
                "fio": result,
            }
            if "global" in self.fio_jobs_dict.keys():
                document["global_options"] = self.fio_jobs_dict["global"]
            processed.append(document)
            if result["jobname"] != "All clients":

                ramp_time = 0
                if "ramp_time" in result["job options"]:
                    ramp_time = int(result["job options"]["ramp_time"])
                elif "ramp_time" in document["global_options"]:
                    ramp_time = int(document["global_options"]["ramp_time"])

                # set start time from s to ms
                start_time = int(end_time) * 1000
                logging_start_time = start_time

                if ramp_time > 0:
                    # set logging start time by adding ramp time to start time (in ms)
                    logging_start_time = start_time + (ramp_time * 1000)

                # The only external method that uses fio_starttime is _log_payload,
                # so we can set time to logging_start_time
                fio_starttime[result["hostname"]] = logging_start_time

                if start_time < earliest_starttime:
                    earliest_starttime = start_time

        return processed, fio_starttime, earliest_starttime

    def _log_payload(self, directory, fio_starttime, job, fio_output_file):  # pod_details
        logs = []
        _current_log_files = deepcopy(_log_files)
        job_options = self.fio_jobs_dict[job]
        if "gtod_reduce" in job_options:
            del _current_log_files["slat"]
            del _current_log_files["clat"]
            del _current_log_files["bw"]
        if "disable_lat" in job_options:
            del _current_log_files["lat"]
        if "disable_slat" in job_options:
            del _current_log_files["slat"]
        if "disable_clat" in job_options:
            del _current_log_files["clat"]
        if "disable_bw" in job_options or "disable_bw_measurement" in job_options:
            del _current_log_files["bw"]
        # find the number of jobs either in the job options or global options
        if "numjobs" in job_options:
            numjob_list = job_options["numjobs"]
        else:
            numjob_list = self.fio_jobs_dict["global"]["numjobs"]

        for log in _current_log_files.keys():
            for host in self.hosts:
                for numjob in range(int(numjob_list)):
                    numjob = numjob + 1
                    log_file_prefix_string = "write_" + str(log) + "_log"
                    if log in ["clat", "slat"]:
                        log_file_prefix_string = "write_lat_log"
                    try:
                        log_file_name = (
                            str(job_options[log_file_prefix_string])
                            + "_"
                            + str(log)
                            + "."
                            + str(numjob)
                            + ".log."
                            + str(host)
                        )
                    except KeyError:
                        try:
                            log_file_name = (
                                str(self.fio_jobs_dict["global"][log_file_prefix_string])
                                + "_"
                                + str(log)
                                + "."
                                + str(numjob)
                                + ".log."
                                + str(host)
                            )

                        except:  # noqa
                            logger.info("Error setting log_file_name")
                    log_file_name = os.path.join(directory, log_file_name)
                    try:
                        with open(log_file_name) as log_file:
                            for log_line in log_file:
                                log_line_values = str(log_line).split(", ")
                                if len(log_line_values) == 5:
                                    timestamp_ms = int(fio_starttime[host]) + int(log_line_values[0])
                                    newtime = datetime.utcfromtimestamp(timestamp_ms / 1000.0)
                                    log_dict = {
                                        "uuid": self.uuid,
                                        "user": self.user,
                                        "host": host,
                                        "cluster_name": self.cluster_name,
                                        "job_number": numjob,
                                        "fio-version": self.fio_version,
                                        "job_options": job_options,
                                        "job_name": str(job),
                                        "log_file": log_file_name,
                                        "sample": int(self.sample),
                                        "log_name": str(log),
                                        "timestamp": timestamp_ms,  # this is in ms
                                        "date": newtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                                        str(_current_log_files[log]["metric"]): int(log_line_values[1]),
                                        # "nodeName": pod_details["hostname"],
                                        "data_direction": _data_direction[int(log_line_values[2])],
                                        "block_size": int(log_line_values[3]),
                                        "offset": int(log_line_values[4]),
                                    }
                                    if "global" in self.fio_jobs_dict.keys():
                                        log_dict["global_options"] = self.fio_jobs_dict["global"]
                                    logs.append(log_dict)
                    except OSError:
                        # In certain situations Fio return code is 0 even after a failed execution, so we have
                        # to check the log file existence to verify this
                        logger.error("Log file %s not found" % log_file_name)
                        exit(1)
        return logs

    def _histogram_payload(
        self, processed_histogram_file, longest_fio_startime, job, numjob=1
    ):  # pod_details
        logs = []
        with open(processed_histogram_file) as log_file:
            for log_line in log_file:
                log_line_values = str(log_line).split(", ")
                if len(log_line_values) == 7 and not (any(len(str(x)) <= 0 for x in log_line_values)):
                    logger.debug(log_line_values)
                    timestamp_ms = int(longest_fio_startime) + int(log_line_values[0])
                    newtime = datetime.utcfromtimestamp(timestamp_ms / 1000.0)
                    log_dict = {
                        "uuid": self.uuid,
                        "user": self.user,
                        "hosts": self.hosts,
                        "cluster_name": self.cluster_name,
                        "fio-version": self.fio_version,
                        "job_options": self.fio_jobs_dict[job],
                        "job_name": str(job),
                        "sample": int(self.sample),
                        "log_name": "clat_hist",
                        "timestamp": timestamp_ms,  # this is in ms
                        "date": newtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                        "number_samples_histogram": int(log_line_values[1]),
                        "min": float(log_line_values[2]),
                        "median": float(log_line_values[3]),
                        "p95": float(log_line_values[4]),
                        "p99": float(log_line_values[5]),
                        "max": float(log_line_values[6]),
                    }
                    if "global" in self.fio_jobs_dict.keys():
                        log_dict["global_options"] = self.fio_jobs_dict["global"]
                    logs.append(log_dict)
        return logs

    def _clean_output(self, fio_output_file):
        cmd = ["sed", "-i", "/{/,$!d", fio_output_file]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip(), stderr, process.returncode

    def _run_fiod(self, fiojob_file, output_dir, fio_output_file):
        cmd = ["fio", "--client=", "path_file", "--output-format=json", "--output="]
        cmd[1] = "--client=" + self.host_file
        cmd[2] = fiojob_file
        cmd[4] = "--output=" + fio_output_file
        logger.info("Executing %s" % " ".join(map(str, cmd)))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=output_dir)
        stdout, stderr = process.communicate()
        return stdout.strip(), stderr, process.returncode

    def _process_histogram(
        self, job, working_dir, processed_histogram_prefix, histogram_output_file, numjob=1
    ):
        histogram_input_file_list = []
        for host in self.hosts:
            input_file = (
                working_dir + "/" + processed_histogram_prefix + "." + str(numjob) + ".log." + str(host)
            )
            histogram_input_file_list.append(input_file)
        logger.debug(histogram_input_file_list)
        if "log_hist_msec" not in self.fio_jobs_dict[job].keys():
            if (
                "global" in self.fio_jobs_dict.keys()
                and "log_hist_msec" not in self.fio_jobs_dict["global"].keys()
            ):
                logger.error("log_hist_msec not found, so can't process histogram logs")
                exit(1)
            else:
                _log_hist_msec = self.fio_jobs_dict["global"]["log_hist_msec"]
        else:
            _log_hist_msec = self.fio_jobs_dict[job]["log_hist_msec"]
        compute_percentiles_from_logs(
            output_csv_file=histogram_output_file,
            file_list=histogram_input_file_list,
            log_hist_msec=_log_hist_msec,
        )

    def _build_fio_job(self, job_name, parent_dir, fio_job_file_name):
        config = configparser.ConfigParser()
        if "global" in self.fio_jobs_dict.keys():
            config["global"] = self.fio_jobs_dict["global"]
        config[job_name] = self.fio_jobs_dict[job_name]
        if os.path.exists(fio_job_file_name):
            logger.info("file " + fio_job_file_name + " already exists. overwriting")
        with open(fio_job_file_name, "w") as configfile:
            config.write(configfile, space_around_delimiters=False)

    def emit_actions(self):
        """
        Executes fio test and calls document parsers, if index_data is true will yield
        normalized data
        """

        # access user specified host file
        with open(self.host_file) as f:
            self.hosts = f.read().splitlines()

        # execute for each job in the user specified job file
        for job in self.fio_jobs:

            job_dir = os.path.join(self.working_dir, job)
            os.makedirs(job_dir, exist_ok=True)
            fio_output_file = os.path.join(job_dir, "fio-result.json")
            fio_job_file = os.path.join(job_dir, "fiojob")
            self._build_fio_job(job, job_dir, fio_job_file)

            # capture sample start time, used for prom data collection
            sample_starttime = datetime.utcnow().strftime("%s")
            stdout, stderr, rc = self._run_fiod(fio_job_file, job_dir, fio_output_file)

            if rc != 0:
                logger.error("Fio failed to execute")
                with open(fio_output_file) as output:
                    logger.error("Output file: %s" % output.read())
                    exit(1)
            stdout, stderr, rc = self._clean_output(fio_output_file)
            if rc != 0:
                logger.error("failed to parse the output file")
                exit(1)
            logger.info(
                "fio has successfully finished sample {} executing for jobname {} and results "
                "are in the dir {}\n".format(self.sample, job, job_dir)
            )

            # capture sample end time, used for prom data collection
            sample_endtime = datetime.utcnow().strftime("%s")
            with open(fio_output_file) as f:
                data = json.load(f)
            fio_endtime = int(data["timestamp"])  # in epoch seconds
            self.fio_version = data["fio version"]

            # parse fio json file, return list of normalized documents and structured start times
            fio_result_documents, fio_starttime, earliest_starttime = self._document_payload(
                data, fio_endtime
            )

            # Add fio result document to fio analyzer object
            self.fio_analyzer_obj.add_fio_result_documents(fio_result_documents, earliest_starttime)

            # from the returned normalized fio json document yield up for indexing
            index = "results"
            for document in fio_result_documents:
                yield document, index

            # check to determine if logs can be parsed, if not fail
            try:
                if self.fio_jobs_dict[job]["filename_format"] != r"f.\$jobnum.\$filenum":  # noqa
                    logger.error(r"filename_format is not 'f.\$jobnum.\$filenum'")  # noqa
                    exit(1)
            except KeyError:
                try:
                    if self.fio_jobs_dict["global"]["filename_format"] != r"f.\$jobnum.\$filenum":  # noqa
                        logger.error(r"filename_format is not 'f.\$jobnum.\$filenum'")  # noqa
                        exit(1)
                except:  # noqa
                    logger.error("Error getting filename_format")

            # parse all fio log files, return list of normalized log documents
            fio_log_documents = self._log_payload(job_dir, fio_starttime, job, fio_output_file)

            # if indexing is turned on yield back normalized data
            index = "log"
            for document in fio_log_documents:
                yield document, index
            if self.histogram_process:
                try:
                    processed_histogram_prefix = self.fio_jobs_dict[job]["write_hist_log"] + "_clat_hist"
                except KeyError:
                    try:
                        processed_histogram_prefix = (
                            self.fio_jobs_dict["global"]["write_hist_log"] + "_clat_hist"
                        )
                    except Exception as err:  # noqa
                        logger.error("Error setting processed_histogram_prefix %s" % err)
                histogram_output_file = (
                    job_dir + "/" + processed_histogram_prefix + "_processed." + str(self.numjob)
                )
                self._process_histogram(job, job_dir, processed_histogram_prefix, histogram_output_file)
                histogram_documents = self._histogram_payload(histogram_output_file, earliest_starttime, job)
                # if indexing is turned on yield back normalized data
                index = "hist-log"
                for document in histogram_documents:
                    yield document, index
            # trigger collection of prom data
            sample_info_dict = {
                "uuid": self.uuid,
                "user": self.user,
                "cluster_name": self.cluster_name,
                "starttime": sample_starttime,
                "endtime": sample_endtime,
                "sample": self.sample,
                "tool": "fio",
                "test_config": self.fio_jobs_dict,
            }

            yield sample_info_dict, "get_prometheus_trigger"
