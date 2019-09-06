from datetime import datetime
from copy import deepcopy
import os
import sys
import json
import subprocess
import logging
#import re
#import numpy as np
#import time


class SmallfileWrapperException(Exception):
    pass

class _trigger_smallfile:
    """
        Will execute with the provided arguments and return normalized results for indexing
    """
    def __init__(self, logger, operations, yaml_input_file, cluster_name, working_dir, result_dir, user, uuid, sample):
        self.logger = logger
        self.operations = operations
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

        #execute for each job in the user specified job file
        operation_list = self.operations.split(',')
        for operation in operation_list:

            json_output_file = os.path.join(self.result_dir, '%s.json' % operation)

            cmd = ["python", "smallfile_cli.py", 
                    "--operation", operation, 
                    "--top", self.working_dir, 
                    "--output-json", json_output_file,
                    "--yaml-input-file", self.yaml_input_file ]
            self.logger.info('running:' + ' '.join(cmd))
            self.logger.info('from current directory %s' % os.getcwd())
            try:
                process = subprocess.check_call(cmd, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                self.logger.exception(e)
                raise SmallfileWrapperException('non-zero process return code %d' % e.returncode)
            self.logger.info("completed sample {} for operation {} , results in {}".format(
                        self.sample, operation, json_output_file))
            with open(json_output_file) as f:
                data = json.load(f)
                yield data, '-results'
