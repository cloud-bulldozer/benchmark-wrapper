#!/bin/bash
# Discover all of the Containerfiles within the repository and create a JSON output
# that can be used to configure a GitHub actions matrix for building each Containerfile
#
# The JSON output looks like this:
#
# {
#   "include": [
#     {
#       "containerfile": path to containerfile relative to repo root,
#       "image_name": name of the image (i.e. name of directory containing the CF)
#       "benchmark": name of the benchmark (i.e. name of directory containing the CF)
#       "env_var": environment variable where image URL will be stored (i.e. <BENCHMARK>_IMAGE)
#       "tag_prefix": prefix of the image tag that should be used (i.e. extension of the CF with a dash)
#       "arch": architecture that the CF should be built on (i.e. extension of the CF, default to amd64)
#     },
#     ...
#   ]
# }
#
output="{\"include\": ["
containerfile_list=(`find snafu/ -name Dockerfile* -o -name Containerfile`)

for cf_index in "${!containerfile_list[@]}"
do
    cf_path="${containerfile_list[$cf_index]}"
    benchmark_name=`echo $cf_path | awk -F "/" '{print $(NF-1)}'`
    benchmark_name=${benchmark_name%_wrapper}
    containerfile_name=`echo $cf_path | awk -F "/" '{print $NF}'`
    arch="amd64"
    if [[ $containerfile_name = *.* ]]
    then
        arch=`echo $cf_path | awk -F "." '{print $NF}'`
        tag_prefix=$arch-
    else
        tag_prefix=""
    fi
    env_var=${benchmark_name^^}_IMAGE


    output="$output{"
    keys=(benchmark containerfile image_name tag_prefix arch env_var)
    values=("${benchmark_name}" "${cf_path}" "${benchmark_name}" "${tag_prefix}" "${arch}" "${env_var}")

    for pair_index in "${!keys[@]}"
    do
        pair="\"${keys[$pair_index]}\": \"${values[$pair_index]}\""  # "keys[i]": "values[i]"
        output="$output$pair"
        if [[ $(($pair_index + 1)) -ne ${#keys[@]} ]]
        then
            output="$output, "
        fi
    done

    output="$output}"

    if [[ $(($cf_index + 1)) -ne ${#containerfile_list[@]} ]]
    then
        output="$output, "
    fi

done

output="$output]}"

echo $output
