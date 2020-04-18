#!/usr/bin/env python
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
import logging
import os

from . import trigger_cluster_loader

logger = logging.getLogger("snafu")


class cluster_loader_wrapper():

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
            '-d', '--dir',
            help='output parent directory, defaults to current directory',
            default=os.path.dirname(os.getcwd()))
        parser.add_argument(
            '-p', '--path-binary',
            help='absolute path to openshift-tests binary',
            default='/root/go/src/github.com/openshift/origin/_output/local/bin/linux/amd64/openshift-tests')
        parser.add_argument(
            '--cl-output',
            help='print the cl output to console ( helps with CI )',
            type=bool)
        parser.add_argument(
            dest="test_name",
            help="name of the test",
            type=str,
            metavar="test_name")
        self.args = parser.parse_args()

        self.cluster_name = "mycluster"
        if "clustername" in os.environ:
            self.cluster_name = os.environ["clustername"]

        self.uuid = ""
        if "uuid" in os.environ:
            self.uuid = os.environ["uuid"]

        self.user = ""
        if "test_user" in os.environ:
            self.user = os.environ["test_user"]
        self.samples = self.args.samples
        self.result_dir = self.args.dir
        self.path_binary = self.args.path_binary
        self.test_name = self.args.test_name
        if self.args.cl_output is not None:
            self.console_cl_output = True
        else:
            self.console_cl_output = False

    def run(self):
        if not os.path.exists(self.result_dir):
            os.mkdir(self.result_dir)
        for s in range(1, self.samples + 1):
            sample_dir = self.result_dir + '/' + str(s)
            if not os.path.exists(sample_dir):
                os.mkdir(sample_dir)
            trigger_generator = trigger_cluster_loader._trigger_cluster_loader(
                logger, self.cluster_name, sample_dir, self.user, self.uuid,
                s, self.path_binary, self.test_name, self.console_cl_output)
            yield trigger_generator
