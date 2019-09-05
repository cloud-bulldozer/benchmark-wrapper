#!/usr/bin/env python
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
import os
import argparse
import configparser
import logging

import trigger_smallfile

logger = logging.getLogger("snafu")

class smallfile_wrapper():

    def __init__(self, parser):
        #collect arguments
        
        # it is assumed that the parser was created using argparse and already knows
        # about the --tool option
        parser.add_argument(
            '-s', '--sample', 
            type=int, 
            help='number of times to run benchmark, defaults to 1',
            default=1)
        parser.add_argument(
            '-d', '--dir', 
            help='output parent directory', 
            default=os.path.dirname(os.getcwd()))
        parse.add_argument(
            '-o', '--operations', 
            help='sequence of smallfile operation types to run',
            default='create')
        parse.add_argument(
            '-y', '--yaml-input-file', 
            help='smallfile parameters passed via YAML input file')
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

        self.sample = self.args.sample
        self.working_dir = self.args.dir
    
    def run(self):
        analyzer_obj = Smallfile_Analyzer(self.uuid, self.user, self.args.cluster_name)
        for i in range(1, self.sample + 1):
            sample_dir = self.working_dir + '/' + str(i)
            if not os.path.exists(sample_dir):
                os.mkdir(sample_dir)
            trigger_generator = trigger_smallfile._trigger_smallfile( self.args.cluster_name,
                                                             sample_dir,
                                                             self.user,
                                                             self.uuid,
                                                             i,
                                                             analyzer_obj)
            yield trigger_generator
    
        yield analyzer_obj
    
