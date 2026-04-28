SHELL := /bin/bash
.DEFAULT_GOAL := help

BLITZ_PATH ?= $(CURDIR)
export PYTHONPATH := $(BLITZ_PATH)

VENV_PYTHON := .venv/bin/python
NAME_FILE := system_data/name.txt
PROTO_GEN_DIR := watchdog/generated
PROTO_FILES := proto/StateLogging.proto proto/PiStatus.proto

UBUNTU_TARGET ?= nathan-hale.local
TARGET_USER ?= ubuntu
SSH_PASS ?= ubuntu
TARGET_PORT ?= 22
TARGET_NAME ?= agathaking
TARGET_FOLDER ?= /opt/blitz/

SERVICE_NAME ?= startup
SERVICE_UNIT_SOURCE := $(BLITZ_PATH)/ops/systemd/watchdog.service
SERVICE_UNIT_PATH ?= /etc/systemd/system/$(SERVICE_NAME).service

.PHONY: help setup rebuild create-python-venv dependencies link wipe set-name ensure-name show-name generate codegen run test install-service deploy-sync deploy deploy-wipe deploy-flash send-to-target restart-service deploy-to-target wipe-target flash-target

help:
	@printf '%s\n' \
		'BLITZ targets:' \
		'  make setup NAME=x             Install deps, venv, links, codegen, name, and service' \
		'  make rebuild                  Regenerate code and reinstall the service' \
		'  make dependencies             Install Ubuntu system packages' \
		'  make set-name NAME=<value>    Persist the local system name' \
		'  make show-name                Print the configured system name' \
		'  make generate                 Generate protobuf Python files' \
		'  make run                      Start the watchdog locally' \
		'  make test                     Run pytest' \
		'  make install-service          Install and restart the systemd watchdog service' \
		'  make wipe                     Remove local system links and service' \
		'  make deploy-sync              Rsync the repo to the target and run setup.sh' \
		'  make deploy                   Sync and restart the target service' \
		'  make deploy-wipe              Run scripts/deploy/wipe_target.sh on the target' \
		'  make deploy-flash TARGET_NAME=x  Run scripts/deploy/flash_target.sh on the target' \

setup: dependencies create-python-venv link generate ensure-name install-service

rebuild: generate create-python-venv ensure-name install-service

create-python-venv:
	@if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
	$(VENV_PYTHON) -m pip install -e .

dependencies:
	bash ./scripts/bootstrap/install_dependencies.sh

link:
	BLITZ_PATH="$(BLITZ_PATH)" \
	bash ./scripts/bootstrap/install_links.sh

wipe:
	SERVICE_NAME="$(SERVICE_NAME)" \
	bash ./scripts/wipe.sh

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

codegen:
	mkdir -p $(PROTO_GEN_DIR)
	protoc -I=proto \
		--python_out=watchdog/generated \
		--pyi_out=watchdog/generated \
		$(PROTO_FILES)

run: ensure-name
	VENV_PYTHON="$(VENV_PYTHON)" \
	BLITZ_PATH="$(BLITZ_PATH)" \
	./scripts/runtime/run_watchdog.sh

test: create-python-venv
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt
	$(VENV_PYTHON) -m pytest

install-service: link ensure-name
	BLITZ_PATH="$(BLITZ_PATH)" \
	SERVICE_NAME="$(SERVICE_NAME)" \
	SERVICE_UNIT_SOURCE="$(SERVICE_UNIT_SOURCE)" \
	SERVICE_UNIT_PATH="$(SERVICE_UNIT_PATH)" \
	bash ./scripts/bootstrap/install_service.sh

deploy-sync:
	UBUNTU_TARGET="$(UBUNTU_TARGET)" \
	TARGET_USER="$(TARGET_USER)" \
	SSH_PASS="$(SSH_PASS)" \
	TARGET_PORT="$(TARGET_PORT)" \
	TARGET_NAME="$(TARGET_NAME)" \
	SERVICE_NAME="$(SERVICE_NAME)" \
	bash ./scripts/deploy/sync_target_install.sh

send-to-target: deploy-sync

deploy: deploy-sync
	UBUNTU_TARGET="$(UBUNTU_TARGET)" \
	TARGET_USER="$(TARGET_USER)" \
	SSH_PASS="$(SSH_PASS)" \
	TARGET_PORT="$(TARGET_PORT)" \
	SERVICE_NAME="$(SERVICE_NAME)" \
	bash ./scripts/deploy/restart_target.sh

restart-service: deploy
deploy-to-target: deploy

deploy-wipe:
	UBUNTU_TARGET="$(UBUNTU_TARGET)" \
	TARGET_USER="$(TARGET_USER)" \
	SSH_PASS="$(SSH_PASS)" \
	TARGET_PORT="$(TARGET_PORT)" \
	SERVICE_NAME="$(SERVICE_NAME)" \
	bash ./scripts/deploy/wipe_target.sh

wipe-target: deploy-wipe

deploy-flash:
	BLITZ_PATH="$(BLITZ_PATH)" \
	UBUNTU_TARGET="$(UBUNTU_TARGET)" \
	TARGET_USER="$(TARGET_USER)" \
	SSH_PASS="$(SSH_PASS)" \
	TARGET_PORT="$(TARGET_PORT)" \
	TARGET_FOLDER="$(TARGET_FOLDER)" \
	TARGET_NAME="$(TARGET_NAME)" \
	SERVICE_NAME="$(SERVICE_NAME)" \
	bash ./scripts/deploy/flash_target.sh

flash-target: deploy-flash
