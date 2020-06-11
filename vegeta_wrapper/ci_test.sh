#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/vegeta:lastest"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/vegeta:$SNAFU_IMAGE_TAG
build_and_push vegeta_wrapper/Dockerfile $image_spec

pushd ripsaw
sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/vegeta/templates/*
# Build new ripsaw image
update_operator_image
source ./tests/test_vegeta.sh
popd
