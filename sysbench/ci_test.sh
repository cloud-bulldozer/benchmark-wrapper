#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
podman build --tag=quay.io/cloud-bulldozer/sysbench:snafu_ci -f sysbench/Dockerfile . && podman push quay.io/cloud-bulldozer/sysbench:snafu_ci

cd ripsaw

sed -i 's/sysbench:latest/sysbench:snafu_ci/g' roles/sysbench/templates/*

# Build new ripsaw image
update_operator_image snafu_ci

# sysbench does not utilize a wrapper from snafu, only the Dockerfile
# We will confirm that the test_sysbench passes only
bash tests/test_sysbench.sh 
