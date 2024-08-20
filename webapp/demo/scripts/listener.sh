#!/bin/bash

while true; do
    received=$(nc -l -p 5002)
    build_dir=$(echo "$received" | jq -r '.build_dir') # Relative to shared volume eg build_dir_name 
    dockerfile_location=$(echo "$received" | jq -r '.dockerfile_location') # Relative to build_dir eg Dockerfile

    if [ -d "$SHARED_VOLUME/$build_dir" ]; then
        ./usr/local/bin/build_and_push.sh "$SHARED_VOLUME/$build_dir" "$dockerfile_location"
    else
        echo "Contents of $SHARED_VOLUME:"
        ls -la "$SHARED_VOLUME"
        echo "Directory not found: $SHARED_VOLUME/$build_dir"
    fi
    sleep 3

done
