#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/image_pull:$SNAFU_IMAGE_TAG
build_and_push snafu/image_pull_wrapper/Dockerfile $image_spec
pushd ripsaw
source tests/test_image_pull.sh
