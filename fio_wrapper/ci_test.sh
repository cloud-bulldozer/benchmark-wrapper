#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/fio:latest"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/fio:$SNAFU_IMAGE_TAG
build_and_push fio_wrapper/Dockerfile $image_spec

cd ripsaw

sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/fio-distributed/templates/*

update_operator_image

get_uuid test_fiod.sh
uuid=`cat uuid`

cd ..

# Define index
index="ripsaw-fio-results ripsaw-fio-log ripsaw-fio-analyzed-result"

check_es "${uuid}" "${index}"
exit $?

