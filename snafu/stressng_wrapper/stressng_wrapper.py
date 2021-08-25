#!/usr/bin/env python

import argparse
import os

from .trigger_stressng import Trigger_stressng


class stressng_wrapper:
    def __init__(self, parent_parser):
        parser_object = argparse.ArgumentParser(
            description="StressNG Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("StressNG benchmark")
        parser.add_argument("-u", "--uuid", nargs=1, help="Provide the uuid")
        parser.add_argument("-j", "--jobfile", help="Provide the jobfile for stressNG", required=True)
        self.args = parser_object.parse_args()

        self.args.runtype = ""
        self.args.timeout = ""
        self.args.vm_stressors = ""
        self.args.vm_bytes = ""
        self.args.mem_stressors = ""

        if "runtype" in os.environ:
            self.args.runtype = os.environ["runtype"]
        if "timeout" in os.environ:
            self.args.timeout = os.environ["timeout"]
        if "vm_stressors" in os.environ:
            self.args.vm_stressors = os.environ["vm_stressors"]
        if "vm_bytes" in os.environ:
            self.args.vm_bytes = os.environ["vm_bytes"]
        if "mem_stressors" in os.environ:
            self.args.mem_stressors = os.environ["mem_stressors"]

    def run(self):
        stressng_wrapper_obj = Trigger_stressng(self.args)
        yield stressng_wrapper_obj
