#!/bin/bash

es_server=${ES_SERVER:-http://foo.esserver.com:9200}

default_operator_image="quay.io/benchmark-operator/benchmark-operator:master"

default_ripsaw_image_prefix="quay.io/cloud-bulldozer"
image_location=${RIPSAW_CI_IMAGE_LOCATION:-quay.io}
image_account=${RIPSAW_CI_IMAGE_ACCOUNT:-rht_perf_ci}
export SNAFU_IMAGE_TAG=${SNAFU_IMAGE_TAG:-snafu_ci}
export SNAFU_WRAPPER_IMAGE_PREFIX="$image_location/$image_account"
echo "posting container images to $image_location with account $image_account"
export image_builder=${SNAFU_IMAGE_BUILDER:-podman}
if [ "$USER" != "root" ] ; then
  SUDO=sudo
fi
NOTOK=1

# see kubernetes initialization on last line of this script
# which will be the first thing the wrapper ci_test.sh does to it

function update_operator_image() {

  WORKLOADS=("hammerdb" "iperf3" "sysbench" "uperf" "vegeta" "scale_openshift" "stressng" "flent" "image_pull" "log_generator")

  for workload in "${WORKLOADS[@]}"; do
      sed -i "s#${default_ripsaw_image_prefix}/${workload}:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/${workload}:${SNAFU_IMAGE_TAG}#g" roles/${workload}/templates/*
  done
  sed -i "s#${default_ripsaw_image_prefix}/fio:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/fio:${SNAFU_IMAGE_TAG}#g" roles/fio_distributed/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/ycsb-server:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/ycsb-server:${SNAFU_IMAGE_TAG}#g" roles/ycsb/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/pgbench:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/pgbench:${SNAFU_IMAGE_TAG}#g"  roles/pgbench/defaults/main.yml
  sed -i "s#${default_ripsaw_image_prefix}/fs-drift:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/fs-drift:${SNAFU_IMAGE_TAG}#g" roles/fs-drift/templates/* roles/fs-drift/tasks/*
  sed -i "s#${default_ripsaw_image_prefix}/smallfile:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/smallfile:${SNAFU_IMAGE_TAG}#g" roles/smallfile/templates/* roles/smallfile/tasks/*
  image_spec=$image_location/$image_account/benchmark-operator:$SNAFU_IMAGE_TAG
  make image-build image-push deploy IMG=$image_spec
  kubectl wait --for=condition=available "deployment/benchmark-controller-manager" -n benchmark-operator --timeout=300s
}

function wait_clean {
  echo "skip"
}

# Takes 2 argumentes. $1 is the Dockerfile path and $2 is the image name
function build_and_push() {
  if ! $SUDO podman build --no-cache --tag=${2} -f ${1} . ; then
    echo "Image building error. Exiting"
    exit 1
  fi
  for i in {1..3}; do
    $SUDO podman push ${2} && break
    if [[ ${i} == 3 ]]; then
      echo "Could not upload image to registry. Exiting"
      exit 1
    fi
  done
}
