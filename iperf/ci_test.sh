#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/iperf3:latest"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/iperf3:$SNAFU_IMAGE_TAG
build_and_push iperf/Dockerfile $image_spec

cd ripsaw

sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/iperf3-bench/templates/*

# Build new ripsaw image
update_operator_image

# iperf does not utilize a wrapper from snafu, only the Dockerfile
# We will confirm that the test_iperf passes only
bash tests/test_iperf3.sh 

