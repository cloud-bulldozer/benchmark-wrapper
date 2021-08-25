#!/usr/bin/env python
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import argparse
import os

import yaml

from .trigger_trex import Trigger_trex


class trex_wrapper:
    def __init__(self, parent_parser):
        parser_object = argparse.ArgumentParser(
            description="TRex Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("TRex traffic benchmark")
        parser.add_argument(
            "--resourcetype",
            default="pod",
            required=False,
            help="Provide the resource type for this trex run - pod/vm/baremetal",
        )
        parser.add_argument("-u", "--uuid", required=True, help="Provide the uuid")
        parser.add_argument("--user", required=False, default="snafu", help="Enter the user")
        self.args = parser_object.parse_args()
        self.args.duration = os.getenv("duration") or os.getenv("DURATION")
        self.args.cluster_name = os.getenv("clustername") or os.getenv("CLUSTERNAME")
        self.args.testpmd_node = os.getenv("testpmd_node") or os.getenv("TESTPMD_NODE")
        self.args.trex_node = os.getenv("trex_node") or os.getenv("TREX_NODE")
        self._set_cfg()

    def _set_cfg(self):
        cpu_file = "/sys/fs/cgroup/cpuset/cpuset.cpus"
        with open(cpu_file) as f:
            coreset = f.read()
        c_list = coreset.rstrip("\n").split(",")
        core_list = list(map(int, c_list))
        pci_list, socket = self._get_pci()
        port_list = self._get_ports()
        config = [
            {
                "version": 2,
                "interfaces": [],
                "port_info": [],
                "c": 0,
                "port_limit": 0,
                "platform": {
                    "master_thread_id": 0,
                    "latency_thread_id": 0,
                    "dual_if": [{"socket": 0, "threads": []}],
                },
            }
        ]
        config_file = "/etc/trex_cfg.yaml"
        config[0]["interfaces"] = pci_list
        config[0]["port_info"] = port_list
        config[0]["c"] = len(core_list) - 2
        config[0]["port_limit"] = len(pci_list)
        config[0]["platform"]["master_thread_id"] = core_list[0]
        config[0]["platform"]["latency_thread_id"] = core_list[1]
        config[0]["platform"]["dual_if"][0]["socket"] = int(socket)
        config[0]["platform"]["dual_if"][0]["threads"] = core_list[2:]
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

    def _get_pci(self):
        pci_address = []
        networks = os.getenv("NETWORK_NAME_LIST") or os.getenv("network_name_list")
        for net in networks.split(","):
            resource = net.split("/")
            pci_device = os.getenv("PCIDEVICE_OPENSHIFT_IO_" + resource[1].upper(), "")
            for pci in pci_device.split(","):
                pci_address.extend([pci.replace("0000:", "")])
                node_file = "/sys/bus/pci/devices/" + pci + "/numa_node"
                with open(node_file) as f:
                    numa_node = f.read()
        return pci_address, numa_node

    def _get_ports(self):
        port_list = []
        src = os.getenv("SOURCE_MAC_LIST") or os.getenv("source_mac_list")
        dest = os.getenv("DEST_MAC_LIST") or os.getenv("dest_mac_list")
        for count in range(len(src.split(","))):
            mac = {}
            mac["src_mac"] = src.split(",")[count]
            mac["dest_mac"] = dest.split(",")[count]
            port_list.append(mac)
        return port_list

    def run(self):
        yield Trigger_trex(self.args)
