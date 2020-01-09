#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
build_and_push fs_drift_wrapper/Dockerfile quay.io/cloud-bulldozer/fs-drift:snafu_ci

cd ripsaw

sed -i 's/fs-drift:master/fs-drift:snafu_ci/g' roles/fs-drift/templates/*

# Build new ripsaw image
update_operator_image snafu_ci

get_uuid test_fs_drift.sh
uuid=`cat uuid`

cd ..

index="ripsaw-fs-drift-results"

check_es $uuid $index
exit $?
