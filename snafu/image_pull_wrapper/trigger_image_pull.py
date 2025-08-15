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
import os
import shutil
import time
from subprocess import PIPE, Popen

logger = logging.getLogger("snafu")


class Trigger_image_pull:
    def __init__(self, args):
        self.uuid = args.uuid
        self.cluster_name = args.cluster_name
        self.user = args.user
        self.pod_name = args.pod_name
        self.pod_count = args.pod_count
        self.timeout = args.timeout
        self.retries = args.retries
        self.image = args.image

    def _json_payload(self, data):
        payload = {
            "uuid": self.uuid,
            "cluster_name": self.cluster_name,
            "pod_name": self.pod_name,
            "timeout": self.timeout,
            "pod_count": self.pod_count,
            "user": self.user,
            "image_retries": self.retries,
            "image": self.image,
        }
        payload.update(data)
        return payload

    def _run_image_pull_test(self):
        logger.info("Running: Podman Pull on supplied image")

        try:
            if not os.path.exists("/tmp/image_pull"):
                os.mkdir("/tmp/image_pull")
        except OSError as err:
            logger.error("Errored while trying to create /tmp/image_pull directory")
            logger.error(err)
            exit(1)

        results = {}
        cmd = ["skopeo", "--insecure-policy", "copy", self.image, "dir:/tmp/image_pull"]

        failures = 0
        while failures <= self.retries:
            # Time the Push
            start_time = datetime.datetime.utcnow()
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output, errors = p.communicate()
            end_time = datetime.datetime.utcnow()

            # Handle Errors
            try:
                assert p.returncode == 0
                success = True
            except Exception:
                success = False
                failures = failures + 1
                logger.info("Failed to pull image: %s" % self.image)
                logger.info("STDOUT: %s" % output)
                logger.info("STDERR: %s" % errors)
                logger.info(f"Retrying. {failures}/{self.retries} failures.")

            # Statistics / Data
            elapsed_time = end_time - start_time
            data = {
                "image": self.image,
                "elapsed_time": elapsed_time.total_seconds(),
                "start_time": start_time,
                "end_time": end_time,
                "failures": failures,
                "successful": success,
            }
            results.update(data)

            if success:
                break
        try:
            shutil.rmtree("/tmp/image_pull")
        except OSError as err:
            logger.error("Errored while trying to delete /tmp/image_pull directory")
            logger.error(err)
        return results

    def emit_actions(self):
        logger.info(
            "Running image pull test with %d image retries and image: %s" % (self.retries, str(self.image))
        )
        logger.info(f"Test UUID is {self.uuid} on cluster {self.cluster_name}")

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        results = self._run_image_pull_test()

        data = {"timestamp": timestamp}
        data.update(results)
        es_data = self._json_payload(data)
        logger.info("Results:")
        logger.info(es_data)
        yield es_data, "results"
        logger.info("Finished executing image pull test")
