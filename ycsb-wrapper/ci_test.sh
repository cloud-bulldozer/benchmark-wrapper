#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
podman build --tag=quay.io/cloud-bulldozer/ycsb-server:snafu_ci -f ycsb-wrapper/Dockerfile . && podman push quay.io/cloud-bulldozer/ycsb-server:snafu_ci

cd ripsaw

sed -i 's/ycsb-server:latest/ycsb-server:snafu_ci/g' roles/load-ycsb/tasks/main.yml

# Build new ripsaw image
update_operator_image snafu_ci

get_uuid test_ycsb.sh
uuid=`cat uuid`

cd ..

index="ripsaw-ycsb-summary"

check_es $uuid $index
exit $?
