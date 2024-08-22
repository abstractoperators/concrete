#!/bin/bash

set -e

build_and_push_image() {
    local build_dir="$1"
    local REPO_NAME=$(basename "$build_dir")

    echo "Processing directory: $build_dir"
    echo "Repo name: $REPO_NAME"
    ls -R $build_dir
    if [ -f "$build_dir/Dockerfile" ]; then
        aws configure list
        aws_account_id=$(aws sts get-caller-identity --query Account --output text)
        aws ecr get-login-password | docker login --username AWS --password-stdin "$aws_account_id.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"

        aws ecr describe-repositories --repository-names ${REPO_NAME} || aws ecr create-repository --repository-name ${REPO_NAME}
        full_image_name="$aws_account_id.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$REPO_NAME"
        docker buildx build --platform linux/arm64 -t "$full_image_name" "$build_dir" &
        build_pid=$!
        wait $build_pid
        if docker push "$full_image_name"; then
            echo 'success'
            ./usr/local/bin/deploy_to_aws.sh $full_image_name
        else
            echo 'fail'
        fi
    else
        echo "No Dockerfile found in $build_dir"
    fi
}

build_and_push_image "$1"
