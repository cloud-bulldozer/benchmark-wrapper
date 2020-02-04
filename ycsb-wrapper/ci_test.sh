#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/ycsb-server:latest"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/ycsb-server:$SNAFU_IMAGE_TAG
build_and_push ycsb-wrapper/Dockerfile $image_spec

cd ripsaw

sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/load-ycsb/tasks/main.yml

# Build new ripsaw image
update_operator_image

get_uuid test_ycsb.sh
uuid=`cat uuid`

cd ..

index="ripsaw-ycsb-summary"

check_es "${uuid}" "${index}"
exit $?
