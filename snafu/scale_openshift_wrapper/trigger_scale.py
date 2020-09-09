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

import logging
import time
from kubernetes import client, config
from openshift.dynamic import DynamicClient

logger = logging.getLogger("snafu")


class Trigger_scale():
    def __init__(self, args):
        self.uuid = args.uuid
        self.user = args.user
        self.scale = args.scale
        self.cluster_name = args.cluster_name
        self.incluster = args.incluster
        self.poll_interval = args.poll_interval
        self.kubeconfig = args.kubeconfig

    def _json_payload(self, data):
        payload = {
            "uuid": self.uuid,
            "cluster_name": self.cluster_name,
        }
        payload.update(data)
        return payload

    def _run_scale(self):
        # Var defs
        machineset_workers = []
        machine_spread = []
        extra = 0
        add_per = 0

        if self.incluster == "true":
            config.load_incluster_config()
            k8s_config = client.Configuration()
            k8s_client = client.api_client.ApiClient(configuration=k8s_config)
        elif self.kubeconfig:
            k8s_client = config.new_client_from_config(self.kubeconfig)
        else:
            k8s_client = config.new_client_from_config()

        dyn_client = DynamicClient(k8s_client)

        nodes = dyn_client.resources.get(api_version='v1', kind='Node')
        machinesets = dyn_client.resources.get(kind='MachineSet')

        worker_count = len(nodes.get(label_selector='node-role.kubernetes.io/worker').attributes.items)\
            or 0
        workload_count = len(nodes.get(label_selector='node-role.kubernetes.io/workload').attributes.items)\
            or 0
        master_count = len(nodes.get(label_selector='node-role.kubernetes.io/master').attributes.items)\
            or 0
        infra_count = len(nodes.get(label_selector='node-role.kubernetes.io/infra').attributes.items)\
            or 0

        infra = dyn_client.resources.get(kind='Infrastructure')
        platform = infra.get().attributes.items[0].spec.platformSpec.type or "Unknown"

        # Machine set name list
        machineset_worker_list = \
            machinesets.get(namespace='openshift-machine-api',
                            label_selector='machine.openshift.io/cluster-api-machine-role!=infra,\
                            machine.openshift.io/cluster-api-machine-role!=workload').attributes.items

        # If we are already at the requested scale exit
        if worker_count == self.scale:
            logger.info("Already at requested worker count")
            return worker_count, master_count, infra_count, workload_count, platform

        logger.info("Current Worker count %s" % (worker_count))

        # Number of workers to add per machine set
        add_per = int(self.scale/len(machineset_worker_list))

        # Additional number of workers to add b/c math
        extra = self.scale % len(machineset_worker_list)

        logger.info("Number of machine sets %s" % (len(machineset_worker_list)))

        for i in range(len(machineset_worker_list)):
            machineset_workers.append(machineset_worker_list[i].metadata.name)
            machine_spread.append(add_per)
        for i in range(extra):
            machine_spread[i] += 1

        logger.info("Machine sets: %s" % (machineset_workers))
        logger.info("New worker per machine set %s" % (machine_spread))

        logger.info("Starting Patching of machine sets")
        # Patch the machinesets
        for i in range(len(machineset_workers)):
            body = {"spec": {"replicas": machine_spread[i]}}
            machinesets.patch(body=body,
                              namespace='openshift-machine-api',
                              name=machineset_workers[i],
                              content_type='application/merge-patch+json')

        # Wait for worker machine sets to show the appropriate ready replicas
        for i in range(len(machineset_workers)):
            new_machine_sets = \
                machinesets.get(namespace='openshift-machine-api',
                                label_selector='machine.openshift.io/cluster-api-machine-role!=infra,\
                                machine.openshift.io/cluster-api-machine-role!=workload').attributes.items
            while new_machine_sets[i].status.readyReplicas != machine_spread[i]:
                if new_machine_sets[i].status.readyReplicas is None and machine_spread[i] == 0:
                    break
                new_machine_sets = \
                    machinesets.get(namespace='openshift-machine-api',
                                    label_selector='machine.openshift.io/cluster-api-machine-role!=infra,\
                                    machine.openshift.io/cluster-api-machine-role!=workload').attributes.items
                time.sleep(self.poll_interval)

        logger.info("Patching of machine sets complete")
        logger.info("Waiting for all workers to be schedulable")
        # Ensure all workers are not listed as unschedulable
        # If we don't do this it will auto-complete a scale-down even though the workers
        # have not been eliminated yet
        new_worker_list = nodes.get(label_selector='node-role.kubernetes.io/worker').attributes.items
        for i in range(len(new_worker_list)):
            while i < len(new_worker_list) and new_worker_list[i].spec.unschedulable:
                new_worker_list = nodes.get(label_selector='node-role.kubernetes.io/worker').attributes.items
                time.sleep(self.poll_interval)
        logger.info("All workers schedulable")

        worker_count = len(nodes.get(label_selector='node-role.kubernetes.io/worker').attributes.items)\
            or 0
        workload_count = len(nodes.get(label_selector='node-role.kubernetes.io/workload').attributes.items)\
            or 0
        master_count = len(nodes.get(label_selector='node-role.kubernetes.io/master').attributes.items)\
            or 0
        infra_count = len(nodes.get(label_selector='node-role.kubernetes.io/infra').attributes.items)\
            or 0

        return worker_count, master_count, infra_count, workload_count, platform

    def emit_actions(self):
        logger.info("Scaling cluster %s to %d workers with uuid %s and polling interval %d" %
                    (self.cluster_name, self.scale, self.uuid, self.poll_interval))
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        start_time = time.time()
        worker_count, master_count, infra_count, workload_count, platform = self._run_scale()
        end_time = time.time()
        elaspsed_time = end_time - start_time
        data = {"timestamp": timestamp,
                "duration": int(elaspsed_time),
                "worker_count": worker_count,
                "master_count": master_count,
                "infra_count": infra_count,
                "workload_count": workload_count,
                "action": "scale",
                "total_count": worker_count+master_count+infra_count+workload_count,
                "platform": platform}
        es_data = self._json_payload(data)
        yield es_data, ''
        logger.info("Finished executing scaling of cluster %s to %d workers" %
                    (self.cluster_name, self.scale))
