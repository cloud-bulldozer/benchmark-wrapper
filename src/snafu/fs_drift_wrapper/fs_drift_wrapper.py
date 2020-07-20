#!/usr/bin/env python
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
import logging
import os

from . import trigger_fs_drift

logger = logging.getLogger("snafu")


class fs_drift_wrapper():

    def __init__(self, parser):
        # collect arguments

        # it is assumed that the parser was created using argparse and already knows
        # about the --tool option
        parser.add_argument(
            '-s', '--samples',
            type=int,
            help='number of times to run benchmark, defaults to 1',
            default=1)
        parser.add_argument(
            '-T', '--top',
            help='directory to access files in')
        parser.add_argument(
            '-d', '--dir',
            help='output parent directory',
            default=os.path.dirname(os.getcwd()))
        parser.add_argument(
            '-y', '--yaml-input-file',
            help='fs-drift parameters passed via YAML input file')
        self.args = parser.parse_args()

        self.server = ""

        self.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.cluster_name = os.environ["clustername"]

        self.uuid = ""
        if "uuid" in os.environ:
            self.uuid = os.environ["uuid"]

        self.user = ""
        if "test_user" in os.environ:
            self.user = os.environ["test_user"]

        if not self.args.top:
            raise SnafuSmfException('must supply directory where you access flies')  # noqa
        self.samples = self.args.samples
        self.working_dir = self.args.top
        self.result_dir = self.args.dir
        self.yaml_input_file = self.args.yaml_input_file

    def run(self):
        if not os.path.exists(self.result_dir):
            os.mkdir(self.result_dir)
        for s in range(1, self.samples + 1):
            sample_dir = self.result_dir + '/' + str(s)
            if not os.path.exists(sample_dir):
                os.mkdir(sample_dir)
            trigger_generator = trigger_fs_drift._trigger_fs_drift(
                logger, self.yaml_input_file, self.cluster_name, self.working_dir, sample_dir,
                self.user, self.uuid, s)
            yield trigger_generator
