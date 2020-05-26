#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/fs-drift:master"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/fs-drift:$SNAFU_IMAGE_TAG
build_and_push src/fs_drift_wrapper/Dockerfile $image_spec

cd ripsaw

sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/fs-drift/templates/* roles/fs-drift/tasks/*

# Build new ripsaw image
update_operator_image

get_uuid test_fs_drift.sh
uuid=`cat uuid`

cd ..

indexes="ripsaw-fs-drift-results ripsaw-fs-drift-rsptimes ripsaw-fs-drift-rates-over-time"
check_es "${uuid}" "${indexes}"
exit $?
