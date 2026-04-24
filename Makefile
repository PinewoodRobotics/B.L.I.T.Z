SHELL := /bin/bash
.DEFAULT_GOAL := help

BLITZ_PATH ?= $(CURDIR)
export PYTHONPATH := $(BLITZ_PATH)

VENV_PYTHON := .venv/bin/python
NAME_FILE := system_data/name.txt
PROTO_GEN_DIR := watchdog/generated

UBUNTU_TARGET ?= nathan-hale.local
TARGET_USER ?= ubuntu
SSH_PASS ?= ubuntu
TARGET_PORT ?= 22
TARGET_NAME ?= agathaking

SERVICE_NAME ?= startup
SERVICE_UNIT_SOURCE := $(BLITZ_PATH)/ops/systemd/watchdog.service
SERVICE_UNIT_PATH ?= /etc/systemd/system/$(SERVICE_NAME).service

help:
	@printf '%s\n' \
		'BLITZ targets:' \
		'  make setup                    Create the venv and install Python deps' \
		'  make deps-ubuntu              Install Ubuntu system packages' \
		'  make set-name NAME=<value>    Persist the local system name' \
		'  make show-name                Print the configured system name' \
		'  make generate                 Generate protobuf Python files' \
		'  make run                      Start the watchdog locally' \
		'  make test                     Run pytest' \
		'  make install-service NAME=x   Setup, codegen, name, install service; sets BLITZ_PATH in /etc' \
		'  make deploy-sync              Rsync the repo to the target machine' \
		'  make deploy                   Sync and restart the target service' \
		'  make deploy-reset TARGET_NAME=x  Recreate target folder and install service remotely' \

setup:
	@if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
	$(VENV_PYTHON) -m pip install -e .

deps-ubuntu:
	sudo apt-get update
	sudo apt install -y protobuf-compiler thrift-compiler git make build-essential pkg-config rustup \
		python3 python3-dev python3-pip python3-venv python3-opencv libssl-dev libclang-dev \
		libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev libgl1-mesa-dev libglu1-mesa-dev \
		libx11-dev libxext-dev libxrender-dev libxrandr-dev libxi-dev libxcursor-dev libxinerama-dev libxss-dev \
		libatlas-base-dev gfortran libblas-dev liblapack-dev libboost-all-dev libtbb-dev sshpass rsync udev

set-name:
	@if [ -z "$(NAME)" ]; then \
		echo "NAME is required. Example: make set-name NAME=dev"; \
		exit 1; \
	fi
	@mkdir -p $(dir $(NAME_FILE))
	@printf '%s\n' "$(NAME)" > "$(NAME_FILE)"
	@echo "Wrote $(NAME_FILE)"

ensure-name:
	@mkdir -p $(dir $(NAME_FILE))
	@if [ -n "$(NAME)" ]; then \
		printf '%s\n' "$(NAME)" > "$(NAME_FILE)"; \
		echo "Wrote $(NAME_FILE)"; \
	elif [ -s "$(NAME_FILE)" ]; then \
		echo "Using existing system name: $$(cat "$(NAME_FILE)")"; \
	else \
		echo "Missing system name. Run 'make set-name NAME=<value>' or pass NAME=<value>."; \
		exit 1; \
	fi

show-name:
	@if [ -s "$(NAME_FILE)" ]; then \
		cat "$(NAME_FILE)"; \
	else \
		echo "No system name configured. Run 'make set-name NAME=<value>'."; \
		exit 1; \
	fi

generate: codegen

codegen: prepare
	mkdir -p $(PROTO_GEN_DIR)
	$(VENV_PYTHON) -m grpc_tools.protoc -I=proto \
		--python_out=watchdog/generated \
		--pyi_out=watchdog/generated \
		proto/StateLogging.proto proto/PiStatus.proto

run: ensure-name
	VENV_PYTHON="$(VENV_PYTHON)" \
	BLITZ_PATH="$(BLITZ_PATH)" \
	./scripts/runtime/run_watchdog.sh

test:
	$(VENV_PYTHON) -m pytest

install-service: setup generate ensure-name
	BLITZ_PATH="$(BLITZ_PATH)" \
	SERVICE_NAME="$(SERVICE_NAME)" \
	SERVICE_UNIT_SOURCE="$(SERVICE_UNIT_SOURCE)" \
	SERVICE_UNIT_PATH="$(SERVICE_UNIT_PATH)" \
	./scripts/bootstrap/install_service.sh

deploy-sync:
	UBUNTU_TARGET="$(UBUNTU_TARGET)" \
	TARGET_USER="$(TARGET_USER)" \
	SSH_PASS="$(SSH_PASS)" \
	TARGET_PORT="$(TARGET_PORT)" \
	TARGET_FOLDER="$(TARGET_FOLDER)" \
	./scripts/deploy/sync_target.sh

send-to-target: deploy-sync

deploy: deploy-sync
	UBUNTU_TARGET="$(UBUNTU_TARGET)" \
	TARGET_USER="$(TARGET_USER)" \
	SSH_PASS="$(SSH_PASS)" \
	TARGET_PORT="$(TARGET_PORT)" \
	SERVICE_NAME="$(SERVICE_NAME)" \
	./scripts/deploy/restart_target.sh

restart-service: deploy
deploy-to-target: deploy

deploy-reset:
	UBUNTU_TARGET="$(UBUNTU_TARGET)" \
	TARGET_USER="$(TARGET_USER)" \
	SSH_PASS="$(SSH_PASS)" \
	TARGET_PORT="$(TARGET_PORT)" \
	TARGET_FOLDER="$(TARGET_FOLDER)" \
	TARGET_NAME="$(TARGET_NAME)" \
	./scripts/deploy/reset_target.sh
