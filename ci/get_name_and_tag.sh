#/bin/bash
# Build the name of an image given the following environment variables:
#
# IMAGE_USER: User within the image registry to publish to
# IMAGE_REPO: User's repository witihn ithe image registry to publish to
# REL_CF_PATH: Relative path to the container file from root of the repository
#
# Will output a sourcable-script to create the following environment variables:
# IMAGE_NAME: $IMAGE_REGISTRY/$IMAGE_USER/$IMAGE_REPO/(name of image based on $REL_CF_PATH)
# IMAGE_TAG_PREFIX: prefix that should be added to image tags
#
# The name of the image is based on the relative path the containerfile and will be set to
# the benchmark's name. The image tag prefix is set to the extension of the containerfile
# followed by a dash.
#
# For instance, if the path is "snafu/benchmarks/uperf/Dockerfile.ppc64le", then
# IMAGE_NAME will be set to "$IMAGE_REGISTRY/$IMAGE_USER/$IMAGE_REPO/uperf" and
# IMAGE_TAG_PREFIX will be set to "ppc64le-"

benchmark_name=`echo $REL_CF_PATH | awk -F "/" '{print $(NF-1)}'`
containerfile_name=`echo $REL_CF_PATH | awk -F "/" '{print $NF}'`
if [[ $containerfile_name = *.* ]]
then
    tag_prefix=`echo $REL_CF_PATH | awk -F "." '{print $NF}'`
    tag_prefix=$tag_prefix-
else
    tag_prefix=""
fi

image_name="${benchmark_name}"
for part in "${IMAGE_REPO}" "${IMAGE_USER}"
do
    if [[ ! -z $part ]]
    then
        image_name=$part/$image_name
    fi
done

echo export IMAGE_NAME=$image_name
echo export IMAGE_TAG_PREFIX=$tag_prefix
