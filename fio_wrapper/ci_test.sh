#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
build_and_push fio_wrapper/Dockerfile quay.io/cloud-bulldozer/fio:snafu_ci

cd ripsaw

sed -i 's/fio:latest/fio:snafu_ci/g' roles/fio-distributed/templates/*

# Build new ripsaw image
update_operator_image snafu_ci

get_uuid test_fiod.sh
uuid=`cat uuid`

cd ..

# Define index
index="ripsaw-fio-results ripsaw-fio-log ripsaw-fio-analyzed-result"

check_es $uuid $index
exit $?
