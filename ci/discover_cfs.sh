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
#       "image_name": name of the image (i.e. name of directory containing the CF)}
#       "tag_prefix": prefix of the image tag that should be used (i.e. extension of the CF)
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
    containerfile_name=`echo $cf_path | awk -F "/" '{print $NF}'`
    if [[ $containerfile_name = *.* ]]
    then
        tag_prefix=`echo $cf_path | awk -F "." '{print $NF}'`
        tag_prefix=$tag_prefix-
    else
        tag_prefix=""
    fi


    output="$output{"
    keys=(containerfile image_name tag_prefix)
    values=("${cf_path}" "${benchmark_name}" "${tag_prefix}")

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
