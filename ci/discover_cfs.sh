#!/bin/bash
# Discover all of the Containerfiles within the repository and create a JSON output
# that can be used to configure a GitHub actions matrix for building each Containerfile
#
# Expects one optional input as the first positional argument. This is the upstream branch name, which
# the current working tree will be compared against in order to understand if a benchmark should
# be labeled as changed or not. If this input is not given, then "master" will be used.
#
# A benchmark will be labeled as changed if any of the following conditions are met:
# * A core component of benchmark-wrapper has changed, known as a 'bone'. Please see $bones for a list of
#   regex searches.
# * Any of the files underneath the benchmark's module path
#
# Note that an exception has been built in for benchmarks that have containerfiles with multiple
# architectures. For instance, if the ppc64le containerfile changes, then only the ppc64le containerfile
# will be rebuilt.
#
# The JSON output looks like this:
#
# {
#   "include": [
#     {
#       "containerfile": path to containerfile relative to repo root,
#       "image_name": name of the image (i.e. name of directory containing the CF)
#       "benchmark": name of the benchmark (i.e. name of directory containing the CF)
#       "env_var": environment variable where image URL will be stored (i.e. <BENCHMARK>_<ARCH>_IMAGE)
#       "tag_prefix": prefix of the image tag that should be used (i.e. extension of the CF with a dash)
#       "arch": architecture that the CF should be built on (i.e. extension of the CF, default to amd64)
#       "changed": whether or not changes have been made which require the benchmark to be tested
#     },
#     ...
#   ]
# }
#
set -e
output="{\"include\": ["
containerfile_list=(`find snafu/ -name Dockerfile* -o -name Containerfile*`)
diff_list=`git diff origin/${1:-master} --name-only`
# last item is anything on TLD
bones=(\
    "ci/" \
    ".github/workflows" \
    "MANIFEST.in" \
    "setup*" \
    "snafu/benchmarks/_*.py" \
    "snafu/*.py" \
    "tox.ini" \
    "version.txt" \
)
bones_changed=false
for bone in "${bones[@]}"
do
    if [[ -n "`echo $diff_list | grep -E \"${bone}\"`" ]]
    then
        bones_changed=true
        break
    fi
done

for cf_index in "${!containerfile_list[@]}"
do
    cf_path="${containerfile_list[$cf_index]}"
    benchmark_dir_name=`echo $cf_path | awk -F "/" '{print $(NF-1)}'`
    benchmark_name=${benchmark_dir_name%_wrapper}
    containerfile_name=`echo $cf_path | awk -F "/" '{print $NF}'`
    arch="amd64"
    if [[ $containerfile_name = *.* ]]
    then
        arch=`echo $cf_path | awk -F "." '{print $NF}'`
        tag_prefix=$arch-
    else
        tag_prefix=""
    fi
    env_var=${benchmark_name^^}_${arch^^}_IMAGE

    if $bones_changed
    then
        changed=true
    else
        # List of files under snafu/benchmark that aren't container files
        changed_bench_files=`echo \
            "$diff_list" | sed '/Dockerfile\|Containerfile/d' | grep "/${benchmark_dir_name}/"`
        # The only containerfile that we care about changing is the one at $cf_path
        if [[ -n `echo $diff_list | grep $cf_path` ]] || [[ -n "${changed_bench_files}" ]]
        then
            changed=true
        else
            changed=false
        fi
    fi

    output="$output{"
    keys=(\
        benchmark \
        containerfile \
        image_name \
        tag_prefix \
        arch \
        env_var \
        changed \
    )
    values=(\
        "${benchmark_name}" \
        "${cf_path}" \
        "${benchmark_name}" \
        "${tag_prefix}" \
        "${arch}" \
        "${env_var}" \
        "${changed}" \
    )

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
