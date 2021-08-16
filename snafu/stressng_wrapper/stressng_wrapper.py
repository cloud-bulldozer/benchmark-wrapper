#!/usr/bin/env python

import os
import argparse

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
        # es custom fields
        self.args.es_ocp_version = ""
        self.args.es_cnv_version = ""
        self.args.es_vm_os_version = ""
        self.args.es_rhcos_version = ""
        self.args.es_kata_version = ""
        self.args.es_kind = ""
        self.args.es_data = ""

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
        # es custom fields
        if "es_ocp_version" in os.environ:
            self.args.es_ocp_version = os.environ["es_ocp_version"]
        if "es_cnv_version" in os.environ:
            self.args.es_cnv_version = os.environ["es_cnv_version"]
        if "es_vm_os_version" in os.environ:
            self.args.es_vm_os_version = os.environ["es_vm_os_version"]
        if "es_rhcos_version" in os.environ:
            self.args.es_rhcos_version = os.environ["es_rhcos_version"]
        if "es_kata_version" in os.environ:
            self.args.es_kata_version = os.environ["es_kata_version"]
        if "es_kind" in os.environ:
            self.args.es_kind = os.environ["es_kind"]
        if "es_data" in os.environ:
            self.args.es_data = os.environ["es_data"]

    def run(self):
        stressng_wrapper_obj = Trigger_stressng(self.args)
        yield stressng_wrapper_obj
