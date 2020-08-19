#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/fs-drift:$SNAFU_IMAGE_TAG 
build_and_push snafu/fs_drift_wrapper/Dockerfile $image_spec
pushd ripsaw
source tests/test_fs_drift.sh
