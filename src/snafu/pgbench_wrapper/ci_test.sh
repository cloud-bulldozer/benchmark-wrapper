#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
default_ripsaw_image="quay.io/cloud-bulldozer/pgbench"
default_ripsaw_tag="latest"
image=$SNAFU_WRAPPER_IMAGE_PREFIX/pgbench
build_and_push pgbench_wrapper/Dockerfile $image:snafu_ci

cd ripsaw

sed -i "s#$default_ripsaw_image#$image#" roles/pgbench/defaults/main.yml
sed -i "s#$default_ripsaw_tag#$SNAFU_IMAGE_TAG#" roles/pgbench/defaults/main.yml

# Build new ripsaw image
update_operator_image

get_uuid test_pgbench.sh
uuid=`cat uuid`

cd ..

index="ripsaw-pgbench-summary ripsaw-pgbench-raw"

check_es "${uuid}" "${index}"
exit $?
