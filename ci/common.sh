#!/bin/bash

es_server="marquez.perf.lab.eng.rdu2.redhat.com"
es_port=9200

function update_operator_image() {
  tag_name=$1
  operator-sdk build quay.io/rht_perf_ci/benchmark-operator:$tag_name --image-builder podman

  # In case we have issues uploading to quay we will retry a few times
  try_count=0
  while [ $try_count -le 2 ]
  do
    if podman push quay.io/rht_perf_ci/benchmark-operator:$tag_name
    then
      try_count=2
    elif [[ $try_count -eq 2 ]]
    then
      echo "Could not upload image to quay. Exiting"
      exit 1
    fi
    ((try_count++))
  done
  sed -i "s|          image: quay.io/benchmark-operator/benchmark-operator:master*|          image: quay.io/rht_perf_ci/benchmark-operator:$tag_name # |" resources/operator.yaml
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
}

# Takes 2 arguements. $1 is the uuid and $2 is a space seperated list of indexs to check
# Returns 0 if ALL indexes are found
function check_es() {
  uuid=$1
  index=${@:2}

  rc=0
  for my_index in $index
  do
    python3 ci/check_es.py -s $es_server -p $es_port -u $uuid -i $my_index
    ec=$?
    if [[ $ec -ne 0 ]]
    then
      exit 1
    fi
  done
  exit 0
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

# Takes 2 argumentes. $1 is the Dockerfile path and $2 is the image name
function build_and_push() {
  if ! podman build --no-cache --tag=${2} -f ${1} . ; then
    echo "Image building error. Exiting"
    exit 1
  fi
  for i in {1..3}; do
    podman push ${2} && break
    if [[ ${i} == 3 ]]; then
      echo "Could not upload image to registry. Exiting"
      exit 1
    fi
  done
}
