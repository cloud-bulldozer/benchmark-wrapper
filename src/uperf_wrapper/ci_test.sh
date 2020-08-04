#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/uperf:$SNAFU_IMAGE_TAG
build_and_push src/uperf_wrapper/Dockerfile $image_spec
pushd ripsaw
source tests/test_uperf.sh
