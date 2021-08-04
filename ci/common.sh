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
  sed -i "s#${default_ripsaw_image_prefix}/fio:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/fio:${SNAFU_IMAGE_TAG}#g" roles/fio_distributed/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/fs-drift:master#${SNAFU_WRAPPER_IMAGE_PREFIX}/fs-drift:${SNAFU_IMAGE_TAG}#g" roles/fs-drift/templates/* roles/fs-drift/tasks/*
  sed -i "s#${default_ripsaw_image_prefix}/hammerdb:master#${SNAFU_WRAPPER_IMAGE_PREFIX}/hammerdb:${SNAFU_IMAGE_TAG}#g" roles/hammerdb/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/iperf3:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/iperf3:${SNAFU_IMAGE_TAG}#g" roles/iperf3/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/pgbench:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/pgbench:${SNAFU_IMAGE_TAG}#g"  roles/pgbench/defaults/main.yml
  sed -i "s#${default_ripsaw_image_prefix}/smallfile:master#${SNAFU_WRAPPER_IMAGE_PREFIX}/smallfile:${SNAFU_IMAGE_TAG}#g" roles/smallfile/templates/* roles/smallfile/tasks/*
  sed -i "s#${default_ripsaw_image_prefix}/sysbench:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/sysbench:${SNAFU_IMAGE_TAG}#g" roles/sysbench/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/uperf:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/uperf:${SNAFU_IMAGE_TAG}#g" roles/uperf/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/ycsb-server:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/ycsb-server:${SNAFU_IMAGE_TAG}#g" roles/ycsb/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/vegeta:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/vegeta:${SNAFU_IMAGE_TAG}#g" roles/vegeta/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/scale_openshift:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/scale_openshift:${SNAFU_IMAGE_TAG}#g" roles/scale_openshift/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/stressng:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/stressng:${SNAFU_IMAGE_TAG}#g" roles/stressng/templates/*
  sed -i "s#${default_ripsaw_image_prefix}/flent:latest#${SNAFU_WRAPPER_IMAGE_PREFIX}/flent:${SNAFU_IMAGE_TAG}#g" roles/flent/templates/*
  image_spec=$image_location/$image_account/benchmark-operator:$SNAFU_IMAGE_TAG
  make image-build image-push deploy IMG=$image_spec
  kubectl wait --for=condition=available "deployment/benchmark-controller-manager" -n benchmark-operator --timeout=300s

  # In case we have issues uploading to quay we will retry a few times
  for i in {1..3}; do
    $SUDO ${image_builder} push ${image_spec} && break
    if [[ ${i} == 3 ]]; then
      echo "Could not upload image to $image_location. Exiting"
      exit $NOTOK
    fi
  done
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
