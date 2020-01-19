#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
build_and_push vdbench_wrapper/Dockerfile quay.io/cloud-bulldozer/vdbench:snafu_ci

cd ripsaw

sed -i 's/vdbench:latest/vdbench:snafu_ci/g' roles/vdbench/templates/*

# Build new ripsaw image
update_operator_image snafu_ci

get_uuid vdbenchd.sh
uuid=`cat uuid`

cd ..

index="ripsaw-vdbench-summary"

check_es $uuid $index
exit $?
