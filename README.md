# B.L.I.T.Z

Battle-Linked Intelligent Tactical Pi Swarm

---

## Function

The function of B.L.I.T.Z is to be the connected swarm of raspberry pi's that all do their own specific task.

## Description

This is primarily made in order to have all the code for similar things in one place rather than scattered over many repositories. However, this mostly contains many standalone code bases that run as different processes and can be made into separate libraries in the future.

## Contains

1. autobahn
   1. essentially the decentralized communication between the processes inside the pi and the other pi's
2. recognition
   1. april tag recognition and distance estimation [to it]
   2. robot image recognition and distance estimation [to it]

## Documentation

The documentation of each "module" can be found in the corresponding folders where the root of the corresponding module is.

### Read Me

## Goal

The main goal of this is to create a code base such that we can put it on a raspberry pi, run one command, and everything is up and running.

## Running the code

Remember to do `pip install -e .` in the root directory to install all the packages.
Also remember do to `make generate-proto` in the root directory to generate the python files from the proto files.



make send-to-target ARGS=13