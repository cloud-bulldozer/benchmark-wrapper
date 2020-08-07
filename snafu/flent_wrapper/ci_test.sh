#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/uperf:latest"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/uperf:$SNAFU_IMAGE_TAG
build_and_push src/uperf_wrapper/Dockerfile $image_spec

cd ripsaw

sed -si "s#$default_ripsaw_image_spec#$image_spec#g" roles/flent/templates/*

# Build new ripsaw image
update_operator_image

get_uuid test_flent.sh
uuid=`cat uuid`

cd ..

index="ripsaw-flent-results"

check_es "${uuid}" "${index}"
exit $?
