#!/bin/bash

while true; do
    build_dir=$(nc -l -s 0.0.0.0 -p 5000)
    if [ -d "$SHARED_VOLUME/$build_dir" ]; then
        ./usr/local/bin/build_and_push.sh "$SHARED_VOLUME/$build_dir"
    else
        echo "Contents of $SHARED_VOLUME:"
        ls -la "$SHARED_VOLUME"
        echo "Directory not found: $SHARED_VOLUME/$build_dir"
    fi
    sleep 3
done