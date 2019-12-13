#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/fs-drift:master"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/fs-drift:$SNAFU_IMAGE_TAG
build_wrapper_image $image_spec fs_drift_wrapper

cd ripsaw

sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/fs-drift/templates/* roles/fs-drift/tasks/*

# Build new ripsaw image
update_operator_image

get_uuid test_fs_drift.sh
uuid=`cat uuid`

cd ..

index="ripsaw-fs-drift-results"

check_es $uuid $index
exit $?
