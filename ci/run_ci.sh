#!/bin/bash

set -x

source ci/common.sh

# Presetting test_choice to be blank.
test_choice=''

while getopts t: flag
do
    case "${flag}" in
        t) test_choice=${OPTARG};;
    esac
done


# Clone ripsaw so we can use it for testing
rm -rf ripsaw
git clone https://github.com/cloud-bulldozer/ripsaw.git --depth 1

# Generate uuid
NEW_UUID=$(uuidgen)
UUID=${NEW_UUID%-*}

if [[ $ghprbPullLongDescription = *"Depends-On:"* ]]; then
  ripsaw_change_id="$(echo -e $ghprbPullLongDescription | sed -n -e 's/^.*Depends-On: //p' | dos2unix)"
  echo $ripsaw_change_id
  cd ripsaw
  git fetch origin pull/$ripsaw_change_id/head:local_change
  git checkout local_change
  cd ..
fi

cd ripsaw
sed -i "s#ES_SERVER#$ES_SERVER#g" tests/test_crs/*
update_operator_image
cd ..

# Podman image prune
podman image prune -a -f

# Prep results.markdown file
cat > results.markdown << EOF
Results for SNAFU CI Test

Test | Result | Runtime
-----|--------|--------
EOF

diff_list=`git diff origin/master --name-only | grep -Ev "*\.(md|png)"`

# Run a full test if:
# - anything in . has been changed (ie run_snafu.py)
# - anything in ci has been changed
# - anything in utils has been changed
# Else only run tests on directories that have changed

if [[ ${test_choice} != '' ]]; then
  echo "Running chosen test: "${test_choice}
  test_list=${test_choice}
elif [[ `echo "${diff_list}" | grep -cv /` -gt 0 || `echo ${diff_list} | grep -E "(ci|utils|image_resources)/|snafu/run_snafu\.py|requirements\.txt"` ]]; then
  echo "Running full test"
  test_list=`find * -maxdepth 3 -name ci_test.sh -type f -exec dirname {} \;`
else
  echo "Running specific tests"
  echo $diff_list
  test_list=`echo "${diff_list}" | awk 'BEGIN{FS=OFS="/"}{NF--; print}' | uniq`
fi

echo -e "Running tests in the following directories:\n${test_list}"
test_rc=0

wait_clean

for dir in ${test_list}; do
  start_time=`date`
  figlet "CI test for ${dir}"
  if [ ! -f $dir/ci_test.sh ]; then
    result="No CI test"
  elif $dir/ci_test.sh; then
    result="PASS"
  else
    result="FAIL"
    test_rc=1
  fi
  end_time=`date`
  duration=`date -ud@$(($(date -ud"$end_time" +%s)-$(date -ud"$start_time" +%s))) +%T`
  echo "${dir} | ${result} | ${duration}" >> results.markdown
  wait_clean
done

echo "Summary of CI Test"
cat results.markdown

exit $test_rc
