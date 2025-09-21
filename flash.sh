#!/bin/bash

name=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            if [ -n "$2" ]; then
                name=$2
                shift 2
            else
                echo "Error: --name requires a value"
                exit 1
            fi
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

if [ -z "$name" ]; then
    echo "Error: --name argument is required"
    exit 1
fi

cd ~/Documents/
git clone https://github.com/PinewoodRobotics/B.L.I.T.Z.git
cd B.L.I.T.Z

# install git submodules
git submodule update --init --recursive

bash scripts/install.sh --name "$name"
