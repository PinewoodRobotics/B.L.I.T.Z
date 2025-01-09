#!/bin/bash

socat -d -d FILE:/dev/ttyUSB0,raw,echo=0 TCP:host.docker.internal:12345