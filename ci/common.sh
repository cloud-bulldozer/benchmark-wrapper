#!/bin/bash

es_server="marquez.perf.lab.eng.rdu2.redhat.com"
es_port=9200
default_operator_image="quay.io/benchmark-operator/benchmark-operator:master"

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
  image_spec=$image_location/$image_account/benchmark-operator:$SNAFU_IMAGE_TAG
  $SUDO operator-sdk build $image_spec --image-builder $image_builder

  # In case we have issues uploading to quay we will retry a few times
  for i in {1..3}; do
    $SUDO ${image_builder} push ${image_spec} && break
    if [[ ${i} == 3 ]]; then
      echo "Could not upload image to $image_location. Exiting"
      exit $NOTOK
    fi
  done
  sed -i \
    "s|          image: $default_operator_image|          image: $image_spec # |" \
    resources/operator.yaml
}

function wait_clean {
  kubectl delete benchmark --all -n my-ripsaw
  kubectl delete all --all -n my-ripsaw
  for i in {1..30}; do
    if [ `kubectl get pods --namespace my-ripsaw | wc -l` -ge 1 ]; then
      sleep 5
    else
      break
    fi
  done
  if [[ `kubectl get namespace my-ripsaw` ]]; then
    kubectl delete namespace my-ripsaw --wait=true
  fi
}

# Takes 2 arguments. $1 is the uuid and $2 is a space-separated list of indexes to check
# Returns 0 if ALL indexes are found
function check_es() {
  if [[ ${#} != 2 ]]; then
    echo "Wrong number of arguments: ${#}"
    exit $NOTOK
  fi
  uuid=$1
  index=${@:2}
  for my_index in $index; do
    python3 ci/check_es.py -s $es_server -p $es_port -u $uuid -i $my_index \
      || exit $NOTOK
  done
}

# Takes test script as parameter and returns the uuid
function get_uuid() {
  my_test=$1
  
  sed -i '/trap finish EXIT/d' tests/$my_test

  rm -f uuid
  (
  source tests/$my_test || :

  # Get UUID
  uuid=`kubectl -n my-ripsaw get benchmarks -o jsonpath='{.items[0].status.uuid}'`

  # while we're here, let's verify that right image location and account got used

  kubectl -n my-ripsaw describe pods | grep -i pulled

  finish
  echo $uuid > uuid
  )
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
