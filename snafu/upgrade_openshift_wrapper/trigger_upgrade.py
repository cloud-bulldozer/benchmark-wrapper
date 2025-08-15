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

import datetime
import logging
import subprocess
import time

from kubernetes import client, config
from openshift.dynamic import DynamicClient

logger = logging.getLogger("snafu")
time_format = "%Y-%m-%dT%H:%M:%S%z"


class Trigger_upgrade:
    def __init__(self, args):
        self.uuid = args.uuid
        self.user = args.user
        self.version = args.version
        self.cluster_name = args.cluster_name
        self.incluster = args.incluster
        self.poll_interval = args.poll_interval
        self.timeout = args.timeout
        self.kubeconfig = args.kubeconfig
        self.toimage = args.toimage
        self.latest = args.latest
        if self.incluster == "true":
            config.load_incluster_config()
            k8s_config = client.Configuration()
            k8s_client = client.api_client.ApiClient(configuration=k8s_config)
        elif self.kubeconfig:
            k8s_client = config.new_client_from_config(self.kubeconfig)
        else:
            k8s_client = config.new_client_from_config()

        self.dyn_client = DynamicClient(k8s_client)

    def _json_payload(self, data):
        payload = {
            "uuid": self.uuid,
            "cluster_name": self.cluster_name,
            "init_version": self.init_version,
            "end_version": self.end_version,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "start_time": self.start_time.strftime(time_format),
        }
        payload.update(data)
        return payload

    def _run_upgrade(self):
        # Get platform
        infra = self.dyn_client.resources.get(kind="Infrastructure")
        platform = infra.get().attributes.items[0].spec.platformSpec.type or "Unknown"

        clusterversion = self.dyn_client.resources.get(kind="ClusterVersion")
        init_version = clusterversion.get().items[0].status.desired.version
        logger.info("Current cluster version is: %s" % init_version)

        # Fail if the upgrade version parameters are not defined
        if not self.toimage and not self.latest and not self.version:
            logging.error(
                "Looks like the version to upgrade to is not set, "
                "please set either toimage or latest or version"
            )
            exit(1)

        # Fail if both toimage and latest parameters are set
        if self.toimage and self.latest:
            logging.error("Looks like both toimage and latest parameters are set, please set one of them")
            exit(1)

        # If an image location was passed
        if self.toimage:
            cmd = ("oc adm upgrade --to-image={} --allow-explicit-upgrade=true --force").format(self.toimage)
        # Upgrade to the latest build available in the channel if set
        elif self.latest:
            cmd = "oc adm upgrade --to-latest=true --allow-upgrade-with-warnings=true --force=true"
        elif self.version:
            cmd = ("oc adm upgrade --to={}").format(self.version)
        logger.info(cmd)
        p = subprocess.run(cmd, shell=True, capture_output=True)

        if p.returncode == 1:
            logger.error("Error executing upgrade command. The error was:")
            logger.error(p.stderr.strip().decode("utf-8"))
            exit(1)

        logger.info(p)

        # Get the desired version after the upgrade has been triggered
        # Desired version field might take few seconds to get updated, wait for it before running the checks
        retries = 0
        desired_version = clusterversion.get().items[0].status.desired.version
        while init_version == desired_version and int(retries) < 10:
            logger.info("Waiting for the configuration to get updated with the desired version")
            time.sleep(3)
            desired_version = clusterversion.get().items[0].status.desired.version
            retries += 1
        logger.info("Desired cluster version is: %s" % desired_version)

        # Exit if the current version is already at the desired version
        if init_version == desired_version:
            logger.info("Cluster version is already at desired version")
            the_time = datetime.datetime.strptime(
                clusterversion.get().attributes.items[0].status.history[0].completionTime, time_format
            )
            return (
                init_version,
                desired_version,
                desired_version,
                platform,
                the_time,
                the_time,
                (the_time - the_time),
            )

        c_state = "incomplete"
        c_version = "0.0.0"
        before = int(time.time())
        while self.timeout * 60 >= int(time.time()) - before and (
            c_state != "Completed" or c_version != desired_version
        ):
            for i in range(10):
                try:
                    cluster_state = clusterversion.get().attributes.items[0].status.history[0]
                except Exception as err:
                    if i == 10:
                        logger.error(err)
                        exit(1)
                    else:
                        logger.warn(err)
                        continue
                else:
                    c_state = cluster_state.state
                    c_version = cluster_state.version
                    break

            if c_state == "Completed" and c_version == desired_version:

                logger.info("Cluster upgrade complete")
                logger.info(clusterversion.get().attributes.items[0].status.history[0])
                break
            status = "oc adm upgrade | grep info"
            s = subprocess.run(status, shell=True, capture_output=True)
            logger.info(s.stdout.strip().decode("utf-8"))
            time.sleep(self.poll_interval)

        new_version = clusterversion.get().items[0].status.desired.version
        logger.info("Cluster version post-upgrade is: %s" % new_version)

        start_time = datetime.datetime.strptime(
            clusterversion.get().attributes.items[0].status.history[0].startedTime, time_format
        )
        end_time = datetime.datetime.strptime(
            clusterversion.get().attributes.items[0].status.history[0].completionTime, time_format
        )
        total_time = end_time - start_time
        logger.info("Total upgrade time: %s" % total_time)

        return init_version, desired_version, new_version, platform, start_time, end_time, total_time

    def get_timings(self):
        logger.info("Getting timing stats from cluster Operators")

        operator_infra = self.dyn_client.resources.get(kind="ClusterOperator")
        operator = operator_infra.get()

        new_docs = [{}]
        for op in operator.attributes.items:
            field_len = len(op.metadata.managedFields)
            op_name = op.metadata.managedFields[field_len - 1].manager
            op_time = datetime.datetime.strptime(op.metadata.managedFields[field_len - 1].time, time_format)
            update_time = op_time - self.start_time
            op_time = op_time.strftime(time_format)
            logger.info(f"Operator: {op_name} finished update at {op_time} and took {update_time}")
            op_data = {
                "operator": op_name,
                "end_time": op_time,
                "update_time": int(update_time.total_seconds()),
            }
            new_docs.append(self._json_payload(op_data))

        return new_docs

    def emit_actions(self):
        # Get the desired upgrade version
        clusterversion = self.dyn_client.resources.get(kind="ClusterVersion")
        desired_version = clusterversion.get().items[0].status.desired.version
        logger.info(
            "Upgrading cluster %s to version %s with uuid %s"
            % (self.cluster_name, desired_version, self.uuid)
        )
        self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        (
            self.init_version,
            self.desired_version,
            self.end_version,
            self.platform,
            self.start_time,
            end_time,
            total_time,
        ) = self._run_upgrade()
        if int(total_time.total_seconds()) != 0:
            docs = self.get_timings()
        else:
            docs = []
        data = {
            "operator": "total",
            "end_time": end_time.strftime(time_format),
            "update_time": int(total_time.total_seconds()),
            "image": self.toimage,
        }
        docs.append(self._json_payload(data))
        for item in docs:
            yield item, ""
        if self.end_version != self.desired_version:
            logger.error("Cluster did not upgrade to desired version")
            logger.error(
                "Cluster version is {} and desired version is {}".format(
                    self.end_version, self.desired_version
                )
            )
            exit(1)
        logger.info("Finished upgrading the cluster to version %s" % (self.desired_version))
