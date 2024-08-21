#!/bin/bash

set -e

build_and_push_image() {
    local build_dir="$1" # eg
    local dockerfile_location="$2"

    echo "Processing directory: $build_dir"
    echo "Dockerfile location: $dockerfile_location"
    echo "Repo name: $REPO_NAME"

    if [ -f "$build_dir/$dockerfile_location" ]; then
        aws configure list
        aws_account_id=$(aws sts get-caller-identity --query Account --output text)
        aws ecr get-login-password | docker login --username AWS --password-stdin "$aws_account_id.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"

        aws ecr describe-repositories --repository-names ${REPO_NAME} || aws ecr create-repository --repository-name ${REPO_NAME}
        full_image_name="$aws_account_id.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$repo_name"
        docker buildx build --platform linux/arm64 -t "$full_image_name" "$build_dir" --file "$dockerfile_location" &
        build_pid=$!
        wait $build_pid
        if docker push "$full_image_name"; then
            echo "Successfully pushed docker image to ECR @ $full_image_name"
        else
            echo "Failed to push docker image to ECR"
        fi
    else
        echo "No Dockerfile found in $build_dir"
    fi
}

build_and_push_image "$1" "$2"
