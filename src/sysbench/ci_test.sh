#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/sysbench:latest"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/sysbench:$SNAFU_IMAGE_TAG
build_and_push src/sysbench/Dockerfile $image_spec

cd ripsaw

sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/sysbench/templates/*

# Build new ripsaw image
update_operator_image

# sysbench does not utilize a wrapper from snafu, only the Dockerfile
# We will confirm that the test_sysbench passes only
bash tests/test_sysbench.sh 
