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

OK = 0

logger = logging.getLogger("snafu")

class _trigger_smallfile:
    """
        Will execute with the provided arguments and return normalized results for indexing
    """
    def __init__(self, operations, clients, cluster_name, working_dir, user, uuid, sample, analyzer_obj):
        self.operations = operations
        self.working_dir = working_dir
        self.user = user
        self.uuid = uuid
        self.sample = sample
        self.analyzer_obj = analyzer_obj
        self.cluster_name = cluster_name

    def emit_actions(self):
        """
        Executes test and calls document parsers, if index_data is true will yield normalized data
        """

        #execute for each job in the user specified job file
        for operation in self.operations:

            op_dir = self.working_dir + '/' + operation
            if not os.path.exists(job_dir):
                os.mkdir(job_dir)
            json_output_file = job_dir + '/' + str('smallfile-result.json')

            cmd = ["python", "smallfile_cli.py", "--top", output_dir, "--output-json", json_output_file]
            logger.debug(cmd)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=output_dir)
            stdout,stderr = process.communicate()
            if process.returncode != OK:
                logger.error("failed to execute a second time, stopping...")
                logger.error(stdout.strip())
                logger.error(stderr.strip())
                exit(1)

            logger.info("successfully finished sample {} executing for operation {} and results are in the dir {}".format(
                        self.sample, operation, op_dir))

            with open(json_output_file) as f:
                data = json.load(f)
                yield data, '-results'
