from copy import deepcopy
import time
import os
import sys
import json
import subprocess
import logging


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
        rsptime_dir = os.path.join(self.working_dir, 'network-shared')

        # clear out any unconsumed response time files in this directory
        if os.path.exists(rsptime_dir):
            contents = os.listdir(rsptime_dir)
            for c in contents:
                if c.endswith('.csv'):
                    os.unlink(os.path.join(rsptime_dir, c))

        json_output_file = os.path.join(self.result_dir, 'fs-drift.json')
        network_shared_dir = os.path.join(self.working_dir, 'network-shared')
        rsptime_file = os.path.join(network_shared_dir, 'stats-rsptimes.csv')
        cmd = ["python", "fs-drift.py", 
                "--top", self.working_dir, 
                "--output-json", json_output_file,
                "--response-times", "Y",
                "--input-yaml", self.yaml_input_file ]
        self.logger.info('running:' + ' '.join(cmd))
        self.logger.info('from current directory %s' % os.getcwd())
        try:
            process = subprocess.check_call(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.logger.exception(e)
            raise FsDriftWrapperException(
                'fs-drift.py non-zero process return code %d' % e.returncode)
        self.logger.info("completed sample {} , results in {}".format(
                    self.sample, json_output_file))
        with open(json_output_file) as f:
            data = json.load(f)
            data['cluster_name'] = self.cluster_name
            data['uuid'] = self.uuid
            data['user'] = self.user
            data['sample'] = self.sample
            yield data, '-results'

        # process response time data

        elapsed_time = float(data['results']['elapsed'])
        start_time = data['results']['start-time']
        sampling_interval = max(int(elapsed_time/120.0), 1)
        cmd = ["python", "rsptime_stats.py",
                "--time-interval", str(sampling_interval),
                rsptime_dir ]
        self.logger.info("process response times with: %s" % ' '.join(cmd))
        try:
            process = subprocess.check_call(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.logger.exception(e)
            raise FsDriftWrapperException(
                'rsptime_stats return code %d' % e.returncode)
        self.logger.info( "response time result {}".format( rsptime_file))
        with open(rsptime_file) as rf:
            lines = [ l.strip() for l in rf.readlines() ]
            start_grabbing = False
            for l in lines:
                if l.startswith('time-since-start'):
                    start_grabbing = True
                elif start_grabbing:
                    if l == '':
                        continue
                    flds = l.split(',')
                    interval = {}
                    interval['cluster_name'] = self.cluster_name
                    interval['uuid'] = self.uuid
                    interval['user'] = self.user
                    interval['sample'] = self.sample
                    rsptime_date = start_time + int(flds[0])
                    rsptime_date_str = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(rsptime_date))
                    interval['date'] = rsptime_date_str
                    # number of fs-drift file operations in this interval
                    interval['op-count'] = int(flds[2])
                    # file operations per second in this interval
                    interval['file-ops-per-sec'] = float(flds[2]) / sampling_interval
                    interval['min'] = float(flds[3])
                    interval['max'] = float(flds[4])
                    interval['mean'] = float(flds[5])
                    interval['50%'] = float(flds[7])
                    interval['90%'] = float(flds[8])
                    interval['95%'] = float(flds[9])
                    interval['99%'] = float(flds[10])
                    yield interval, '-rsptimes'
