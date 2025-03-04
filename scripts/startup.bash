#!/bin/bash

# Check if the name file exists
if [ ! -f "name.txt" ]; then
    echo "Error: name.txt does not exist"
    exit 1
fi

make watchdog