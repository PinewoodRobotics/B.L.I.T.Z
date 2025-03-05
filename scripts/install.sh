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

output_file="name.txt"

echo "${name}" > "${output_file}"

echo "Successfully created ${output_file}"

make initiate-project
make generate-proto

sudo cp scripts/startup.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable startup
sudo systemctl restart startup