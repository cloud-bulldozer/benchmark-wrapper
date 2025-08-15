#!/usr/bin/env python3

import datetime
import logging
import subprocess

import yaml

logger = logging.getLogger("snafu")


class Trigger_stressng:
    def __init__(self, args):
        self.uuid = args.uuid
        self.runtype = args.runtype
        self.timeout = args.timeout
        self.vm_stressors = args.vm_stressors
        self.vm_bytes = args.vm_bytes
        self.mem_stressors = args.mem_stressors
        self.jobfile = args.jobfile

    def _run_stressng(self):
        cmd = f"stress-ng --job {self.jobfile} --log-file stressng.log -Y stressng.yml"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.strip().decode("utf-8"), process.returncode

    def _parse_outfile(self):
        stream = open("stressng.yml")
        data = yaml.load(stream, Loader=yaml.FullLoader)
        metrics = data["metrics"]
        results = []
        for metric in metrics:
            stressor = metric["stressor"]
            bogoops = metric["bogo-ops"]
            result = {stressor: bogoops}
            results.append(result)
        return results

    def _json_payload(self, data, uuid, runtype, timeout, vm_stressors, vm_bytes, mem_stressors, timestamp):
        logger.info("generating json payload")
        edict = {}
        processed = []
        edict.update(
            {
                "workload": "stressng",
                "uuid": uuid,
                "runtype": runtype,
                "timeout": timeout,
                "vm_stressors": vm_stressors,
                "vm_bytes": vm_bytes,
                "mem_stressors": mem_stressors,
                "timestamp": timestamp,
            }
        )
        for i in range(len(data)):
            edict.update(dict(data[i]))
        processed.append(edict)
        return processed

    def _summarize_data(self, data, timestamp):
        print("Summarizing data")
        print("")
        print("+{} stress-NG Results {}+".format("-" * (50), "-" * (50)))
        print("stressNG setup")
        print("")
        print("workload: {}".format(data[0]["workload"]))
        print("uuid: {}".format(data[0]["uuid"]))
        print("runtype: {}".format(data[0]["runtype"]))
        print("timeout: {}".format(data[0]["timeout"]))
        print("vm_stressors: {}".format(data[0]["vm_stressors"]))
        print("vm_bytes: {}".format(data[0]["vm_bytes"]))
        print("timestamp: {}".format(data[0]["timestamp"]))
        print("results:")
        if "cpu" in data[0].keys():
            print("cpu bogomips: {}".format(data[0]["cpu"]))
        if "vm" in data[0].keys():
            print("vm bogomips: {}".format(data[0]["vm"]))
        if "mem" in data[0].keys():
            print("mem bogomips: {}".format(data[0]["mem"]))
        print("+{}  {}+".format("-" * (50), "-" * (50)))

    def emit_actions(self):
        timestamp = datetime.datetime.now()
        logger.info("Starting stress-ng")
        stdout = self._run_stressng()
        if stdout[1] == 1:
            logger.info("stressng failed to execute, trying one more time..")
            stdout = self._run_stressng()
            if stdout[1] == 1:
                logger.info("stressng failed to execute a second time, stopping...")
                exit(1)
        logger.info("Starting output parsing")
        data = self._parse_outfile()
        logger.info(data)
        documents = self._json_payload(
            data,
            self.uuid,
            self.runtype,
            self.timeout,
            self.vm_stressors,
            self.vm_bytes,
            self.mem_stressors,
            timestamp,
        )
        if len(documents) > 0:
            logger.info("Summarizing data")
            self._summarize_data(documents, timestamp)
        if len(documents) > 0:
            for document in documents:
                yield document, "results"
        else:
            raise Exception("Failed to produce stressng results document")
