#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image_spec="quay.io/cloud-bulldozer/hammerdb:master"
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/hammerdb:$SNAFU_IMAGE_TAG
build_and_push hammerdb/Dockerfile $image_spec

cd ripsaw

sed -i "s#$default_ripsaw_image_spec#$image_spec#g" roles/hammerdb/templates/*

# Build new ripsaw image
update_operator_image

get_uuid test_hammerdb.sh
uuid=`cat uuid`

cd ..

index="ripsaw-hammerdb-results"

check_es "${uuid}" "${index}"
exit $?
