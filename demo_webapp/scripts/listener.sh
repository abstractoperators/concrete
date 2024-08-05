#!/bin/bash

SHARED_DIR="/shared"

while true; do
    build_dir=$(nc -l -p 5002)
    if [ -d "$SHARED_DIR/$build_dir" ]; then
        ./usr/local/bin/build_and_push.sh "$SHARED_DIR/$build_dir"
    else
        echo "Contents of $SHARED_DIR:"
        ls -la "$SHARED_DIR"
        echo "Directory not found: $SHARED_DIR/$build_dir"
    fi
    sleep 3
done