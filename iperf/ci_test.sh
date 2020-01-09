#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
build_and_push iperf/Dockerfile quay.io/cloud-bulldozer/iperf:snafu_ci

cd ripsaw

sed -i 's/iperf:latest/iperf:snafu_ci/g' roles/iperf3-bench/templates/*

# Build new ripsaw image
update_operator_image snafu_ci

# iperf does not utilize a wrapper from snafu, only the Dockerfile
# We will confirm that the test_iperf passes only
bash tests/test_iperf3.sh 
