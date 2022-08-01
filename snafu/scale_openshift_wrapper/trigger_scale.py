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

import json
import logging
import subprocess
import time
from shutil import which

from kubernetes import client, config
from openshift.dynamic import DynamicClient
from packaging import version

logger = logging.getLogger("snafu")


class Trigger_scale:
    def __init__(self, args):
        self.uuid = args.uuid
        self.user = args.user
        self.scale = args.scale
        self.cluster_name = args.cluster_name
        self.incluster = args.incluster
        self.poll_interval = args.poll_interval
        self.kubeconfig = args.kubeconfig
        self.is_rosa = False
        if args.rosa_cluster is not None:
            logger.info("Identified ROSA for scaling process")
            if args.rosa_token is None:
                logger.error("--rosa-token is required when --rosa is true")
                exit(1)
            else:
                self.rosa_token = args.rosa_token
            if which("rosa") is None:
                logger.error("ROSA tool not found")
                exit(1)
            else:
                # required rosa version >= 1.0.10
                self.rosa_tool = which("rosa")
                logger.info("Checking ROSA version")
                rosa_command = [self.rosa_tool, "version"]
                logger.debug(rosa_command)
                rosa_process = subprocess.Popen(rosa_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                rosa_stdout, rosa_stderr = rosa_process.communicate()
                if rosa_process.returncode != 0:
                    logger.error("Unable to execute %s" % rosa_command)
                    logger.error(rosa_stderr.strip().decode("utf-8"))
                    exit(1)
                else:
                    logger.debug(rosa_stdout.strip().decode("utf-8"))
                    rosa_version = rosa_stdout.strip().decode("utf-8")
                    logger.info("Detected ROSA version %s" % rosa_version)
                    if version.parse(rosa_stdout.strip().decode("utf-8")) < version.parse("1.0.10"):
                        logger.error("Minimum ROSA version required: 1.0.10")
                        exit(1)
            self.cluster_name = args.rosa_cluster
            self.rosa_env = args.rosa_env
            self._rosa_login()
            logger.info("ROSA login completed")
            self.is_rosa = True

    def _json_payload(self, data):
        payload = {
            "uuid": self.uuid,
            "cluster_name": self.cluster_name,
        }
        payload.update(data)
        return payload

    def _rosa_login(self):
        logger.info("Attempting to log in ROSA")
        rosa_command = [self.rosa_tool, "login", "--token=" + self.rosa_token]
        if self.rosa_env:
            rosa_command.append("--env=" + self.rosa_env)
        logger.debug(rosa_command)
        rosa_process = subprocess.Popen(rosa_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rosa_stdout, rosa_stderr = rosa_process.communicate()
        if rosa_process.returncode != 0:
            logger.error("Unable to execute %s" % rosa_command)
            logger.error(rosa_stderr.strip().decode("utf-8"))
            exit(1)
        else:
            logger.debug(rosa_stdout.strip().decode("utf-8"))

    def _rosa_getmachinepools(self):
        logger.info("Getting machinepools information for cluster: %s" % (self.cluster_name))
        rosa_command = [self.rosa_tool, "list", "machinepools", "-c", self.cluster_name, "-o", "json"]
        logger.debug(rosa_command)
        rosa_process = subprocess.Popen(rosa_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rosa_stdout, rosa_stderr = rosa_process.communicate()
        if rosa_process.returncode != 0:
            logger.error("Unable to execute %s" % rosa_command)
            logger.error(rosa_stderr.strip().decode("utf-8"))
            exit(1)
        return json.loads(rosa_stdout)

    def _rosa_scale(self, machinepool):
        logger.info(
            "Attempting to scale machinepool %s of %s to %d" % (machinepool, self.cluster_name, self.scale)
        )
        for i in self.rosa_machinepools:
            if i["id"] == machinepool:
                azs = len(i["availability_zones"])
                if self.scale % azs != 0:
                    logger.error(
                        "%d is not multiple of %d (workers must be a multiple of AZs on ROSA)"
                        % (self.scale, azs)
                    )
                    exit(1)
        rosa_command = [
            self.rosa_tool,
            "edit",
            "machinepool",
            "-c",
            self.cluster_name,
            "--replicas",
            str(self.scale),
            machinepool,
        ]
        logger.debug(rosa_command)
        rosa_process = subprocess.Popen(rosa_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rosa_stdout, rosa_stderr = rosa_process.communicate()
        if rosa_process.returncode != 0:
            logger.error("Unable to execute %s" % rosa_command)
            logger.error(rosa_stderr.strip().decode("utf-8"))
            exit(1)

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

        try:
            dyn_client = DynamicClient(k8s_client)
        except Exception as err:
            logger.error("Could not configure client, failing the run")
            logger.error(err)
            exit(1)

        if self.is_rosa:
            self.rosa_machinepools = self._rosa_getmachinepools()
            logger.debug("ROSA MachinePools: %s" % self.rosa_machinepools)

        try:
            nodes = dyn_client.resources.get(api_version="v1", kind="Node")
            machinesets = dyn_client.resources.get(kind="MachineSet")
        except Exception as err:
            logger.error("Could not get information on nodes/machinesets, failing the run")
            logger.error(err)
            exit(1)

        clusterversion = dyn_client.resources.get(kind="ClusterVersion")
        openshift_version = clusterversion.get().items[0].status.desired.version
        network_type = dyn_client.resources.get(kind="Network", api_version="config.openshift.io/v1")
        network_type = network_type.get().attributes.items[0].spec.networkType

        worker_count = (
            len(
                nodes.get(
                    label_selector="node-role.kubernetes.io/worker,"
                    "!node-role.kubernetes.io/master,"
                    "!node-role.kubernetes.io/infra,"
                    "!node-role.kubernetes.io/workload"
                ).attributes.items
            )
            or 0
        )
        workload_count = (
            len(nodes.get(label_selector="node-role.kubernetes.io/workload").attributes.items) or 0
        )
        master_count = len(nodes.get(label_selector="node-role.kubernetes.io/master").attributes.items) or 0
        infra_count = len(nodes.get(label_selector="node-role.kubernetes.io/infra").attributes.items) or 0
        init_workers = worker_count

        infra = dyn_client.resources.get(kind="Infrastructure")

        try:
            platform = infra.get().attributes.items[0].spec.platformSpec.type
        except Exception as err:
            logger.error("Platform type not obtained through spec.platformSpec.type")
            logger.error("Trying to query status.platform")
            logger.error(err)

            try:
                platform = infra.get().attributes.items[0].status.platform
            except Exception as err:
                logger.error("Could not identify platform. Marking as Unknown")
                logger.error(err)
                platform = "Unknown"

        # Machine set name list
        machineset_all_list = machinesets.get(namespace="openshift-machine-api").attributes.items

        machineset_worker_list = []

        for i in range(len(machineset_all_list)):
            if (
                machineset_all_list[i].spec.template.metadata.labels[
                    "machine.openshift.io/cluster-api-machine-role"
                ]
                == "worker"
            ):
                machineset_worker_list.append(machineset_all_list[i])
        # If we are already at the requested scale exit
        # Determine if we are scaling down or up
        action = "scale_nochange"
        if int(worker_count) == int(self.scale):
            logger.info("Already at requested worker count")
            return (
                init_workers,
                worker_count,
                master_count,
                infra_count,
                workload_count,
                platform,
                action,
                openshift_version,
                network_type,
            )
        elif int(worker_count) > int(self.scale):
            action = "scale_down"
        else:
            action = "scale_up"

        logger.info("Current Worker count %s" % (worker_count))

        # Number of workers to add per machine set
        add_per = int(self.scale / len(machineset_worker_list))

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
        if not self.is_rosa:
            for i in range(len(machineset_workers)):
                body = {"spec": {"replicas": machine_spread[i]}}
                machinesets.patch(
                    body=body,
                    namespace="openshift-machine-api",
                    name=machineset_workers[i],
                    content_type="application/merge-patch+json",
                )
        else:
            self._rosa_scale("Default")

        logger.info("Waiting for worker machine set to show the appropiate ready replicas")
        for i in range(len(machineset_worker_list)):
            new_machine_sets = machinesets.get(
                namespace="openshift-machine-api", name=machineset_worker_list[i].metadata.name
            )
            while new_machine_sets.status.readyReplicas != machine_spread[i]:
                if new_machine_sets.status.readyReplicas is None and machine_spread[i] == 0:
                    break
                new_machine_sets = machinesets.get(
                    namespace="openshift-machine-api", name=machineset_worker_list[i].metadata.name
                )
                logger.debug(
                    "Number of ready replicas for %s: %s. Waiting %d seconds for next check..."
                    % (
                        new_machine_sets.metadata.name,
                        str(new_machine_sets.status.readyReplicas),
                        self.poll_interval,
                    )
                )
                time.sleep(self.poll_interval)

        logger.info("Patching of machine sets complete")
        logger.info("Waiting for all workers to be schedulable")
        # Ensure all workers are not listed as unschedulable
        # If we don't do this it will auto-complete a scale-down even though the workers
        # have not been eliminated yet
        new_worker_list = nodes.get(label_selector="node-role.kubernetes.io/worker").attributes.items
        for i in range(len(new_worker_list)):
            while i < len(new_worker_list) and new_worker_list[i].spec.unschedulable:
                new_worker_list = nodes.get(label_selector="node-role.kubernetes.io/worker").attributes.items
                logger.debug(
                    "Number of ready workers: %d. Waiting %d seconds for next check..."
                    % (len(new_worker_list), self.poll_interval)
                )
                time.sleep(self.poll_interval)
        logger.info("All workers schedulable")

        worker_count = (
            len(
                nodes.get(
                    label_selector="node-role.kubernetes.io/worker,!node-role.kubernetes.io/master"
                ).attributes.items
            )
            or 0
        )
        workload_count = (
            len(nodes.get(label_selector="node-role.kubernetes.io/workload").attributes.items) or 0
        )
        master_count = len(nodes.get(label_selector="node-role.kubernetes.io/master").attributes.items) or 0
        infra_count = len(nodes.get(label_selector="node-role.kubernetes.io/infra").attributes.items) or 0

        return (
            init_workers,
            worker_count,
            master_count,
            infra_count,
            workload_count,
            platform,
            action,
            openshift_version,
            network_type,
        )

    def emit_actions(self):
        logger.info(
            "Scaling cluster %s to %d workers with uuid %s and polling interval %d"
            % (self.cluster_name, self.scale, self.uuid, self.poll_interval)
        )
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        start_time = time.time()
        (
            init_workers,
            worker_count,
            master_count,
            infra_count,
            workload_count,
            platform,
            action,
            openshift_version,
            network_type,
        ) = self._run_scale()
        end_time = time.time()
        elaspsed_time = end_time - start_time
        data = {
            "timestamp": timestamp,
            "duration": int(elaspsed_time),
            "worker_count": worker_count,
            "master_count": master_count,
            "infra_count": infra_count,
            "workload_count": workload_count,
            "init_worker_count": init_workers,
            "action": action,
            "total_count": worker_count + master_count + infra_count + workload_count,
            "platform": platform,
            "openshift_version": openshift_version,
            "network_type": network_type,
        }
        es_data = self._json_payload(data)
        yield es_data, ""
        logger.info(
            "Finished executing scaling of cluster %s to %d workers" % (self.cluster_name, self.scale)
        )
