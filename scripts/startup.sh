#!/bin/bash

set -x

echo "Starting startup script"

cd "$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/../"

# Check if the name file exists
if [ ! -f "name.txt" ]; then
    echo "Error: name.txt does not exist"
    exit 1
fi

make watchdog