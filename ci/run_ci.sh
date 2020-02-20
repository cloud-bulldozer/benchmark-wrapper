#/bin/bash

set -x

source ci/common.sh

wait_clean

kubectl create namespace my-ripsaw

# Clone ripsaw so we can use it for testing
rm -rf ripsaw
git clone https://github.com/cloud-bulldozer/ripsaw.git

if [[ $ghprbPullLongDescription = *"Depends-On:"* ]]; then
  ripsaw_change_id="$(echo $ghprbPullLongDescription | sed -n -e 's/^.*Depends-On: //p')"
  echo $ripsaw_change_id
  cd ripsaw
  git fetch origin pull/$ripsaw_change_id/head:local_change
  git checkout local_change
  cd ..
fi


# Prep results.markdown file
echo "Results for SNAFU CI Test" > results.markdown
echo "" >> results.markdown
echo 'Test | Result | Runtime' >> results.markdown
echo '-----|--------|--------' >> results.markdown

diff_list=`git diff origin/master --name-only`

# Run a full test if:
# - anything in . has been changed (ie run_snafu.py)
# - anything in ci has been changed
# - anything in utils has been changed
# Else only run tests on directories that have changed
if [[ `echo $diff_list | grep -v / | wc -l` -gt 0 || `echo $diff_list | grep ci/` || `echo $diff_list | grep utils/` ]]
then
  echo "Running full test"
  test_list=`ls -d */ | grep -Ev "(utils|ci|ripsaw|image_resources)/"`
else
  echo "Running specific tests"
  echo $diff_list
  test_list=`echo $diff_list | awk -F "/" '{print $1}' | uniq`
fi

echo "Running tests in the following directories: "$test_list
test_rc=0

for dir in `echo $test_list`
do
  my_dir=${dir}
  if [ -f $my_dir/ci_test.sh ]; then
    start_time=`date`
    figlet "CI test for "$my_dir
    if $my_dir/ci_test.sh
    then
      end_time=`date`
      duration=`date -ud@$(($(date -ud"$end_time" +%s)-$(date -ud"$start_time" +%s))) +%T`
      echo ${dir::-1}" | PASS | "$duration >> results.markdown
    else
      end_time=`date`
      duration=`date -ud@$(($(date -ud"$end_time" +%s)-$(date -ud"$start_time" +%s))) +%T`
      echo ${dir::-1}" | FAIL | "$duration >> results.markdown
      test_rc=1
    fi
    wait_clean
  fi
done

echo "Summary of CI Test"
cat results.markdown

exit $test_rc
