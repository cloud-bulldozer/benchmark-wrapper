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

NOTOK=1

# see kubernetes initialization on last line of this script
# which will be the first thing the wrapper ci_test.sh does to it

function update_operator_image() {
  image_spec=$image_location/$image_account/benchmark-operator:$SNAFU_IMAGE_TAG
  operator-sdk build $image_spec --image-builder $image_builder

  # In case we have issues uploading to quay we will retry a few times
  try_count=0
  while [ $try_count -le 2 ]
  do
    if $image_builder push $image_spec
    then
      try_count=2
    elif [[ $try_count -eq 2 ]]
    then
      echo "Could not upload image to $image_location. Exiting"
      exit $NOTOK
    fi
    ((try_count++))
  done
  sed -i \
    "s|          image: $default_operator_image|          image: $image_spec # |" \
    resources/operator.yaml
}

function build_wrapper_image() {
  image_spec=$1
  wrapper_dir=$2
  if [ "$image_builder" = "docker" ] ; then
    docker build --tag=$image_spec -f $wrapper_dir/Dockerfile . && docker push $image_spec
  elif [ "$image_builder" = "podman" ] ; then
    buildah bud --tag $image_spec -f $wrapper_dir/Dockerfile . && podman push $image_spec
  fi
}

function wait_clean {
  kubectl delete all --all -n my-ripsaw
  for i in {1..30}; do
    if [ `kubectl get pods --namespace my-ripsaw | wc -l` -ge 1 ]; then
      sleep 5
    else
      break
    fi
  done
  kubectl delete namespace my-ripsaw
  kubectl create namespace my-ripsaw || exit $NOTOK
}

# Takes 2 arguments. $1 is the uuid and $2 is a space-separated list of indexes to check
# Returns 0 if ALL indexes are found
function check_es() {
  uuid=$1
  index=${@:2}

  rc=0
  for my_index in $index
  do
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

  finish
  echo $uuid > uuid
  )
}

# initialization of K8S for ripsaw

wait_clean
