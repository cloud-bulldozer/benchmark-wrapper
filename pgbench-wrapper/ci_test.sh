#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
podman build --tag=quay.io/cloud-bulldozer/pgbench:snafu_ci -f pgbench-wrapper/Dockerfile . && podman push quay.io/cloud-bulldozer/pgbench:snafu_ci

cd ripsaw

sed -i 's/latest/snafu_ci/g' roles/pgbench/defaults/main.yml

# Build new ripsaw image
update_operator_image snafu_ci

get_uuid test_pgbench.sh
uuid=`cat uuid`

cd ..

index="ripsaw-pgbench-summary"

check_es $uuid $index
exit $?
