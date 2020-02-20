#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/smallfile:master"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/smallfile:$SNAFU_IMAGE_TAG
build_and_push smallfile_wrapper/Dockerfile $image_spec

cd ripsaw

sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/smallfile-bench/templates/* roles/smallfile-bench/tasks/*

# Build new ripsaw image
update_operator_image

get_uuid test_smallfile.sh
uuid=`cat uuid`

cd ..

index="ripsaw-smallfile-results ripsaw-smallfile-rsptimes"

check_es "${uuid}" "${index}"
exit $?

