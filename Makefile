export PYTHONPATH := $(shell pwd)
ARGS ?=

VENV_PYTHON := .venv/bin/python

PROTO_DIR = proto
PROTO_GEN_DIR = watchdog/generated

.PHONY: watchdog
watchdog:
	$(VENV_PYTHON) -u watchdog/main.py
initiate-project:
	if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip install -e .

mac-deps:
	brew install sshpass

prepare:
	mkdir -p $(PROTO_GEN_DIR)
	touch $(PROTO_GEN_DIR)/__init__.py

generate: prepare
	protoc -I=$(PROTO_DIR) \
		--python_out=$(PROTO_GEN_DIR) \
		--pyi_out=$(PROTO_GEN_DIR) \
		$(shell find $(PROTO_DIR) -name "*.proto")
	.venv/bin/fix-protobuf-imports $(PROTO_GEN_DIR)

flash:
	./scripts/flash.bash $(ARGS)


UBUNTU_TARGET = raspberrypi1.local
SSH_PASS = ubuntu

send-to-target:
	sshpass -p $(SSH_PASS) rsync -av --progress --exclude-from=.gitignore --delete ./ ubuntu@$(UBUNTU_TARGET):~/Documents/B.L.I.T.Z/

UBUNTU_TARGET_NAME = "agathaking"
hard-reset:
	sshpass -p $(SSH_PASS) ssh ubuntu@$(UBUNTU_TARGET) 'sudo rm -rf /home/ubuntu/Documents/B.L.I.T.Z/ && mkdir -p /home/ubuntu/Documents/B.L.I.T.Z/'
	$(MAKE) send-to-target
	sshpass -p $(SSH_PASS) ssh ubuntu@$(UBUNTU_TARGET) 'cd ~/Documents/B.L.I.T.Z/ && bash scripts/install.sh --name $(UBUNTU_TARGET_NAME)'

test:
	$(VENV_PYTHON) -m pytest

download-replays:
	@echo "Downloading replay file from remote server..."
	scp ubuntu@10.47.65.7:~/Documents/B.L.I.T.Z/replay-2025-08-20_21-13-00.db ./replay-2025-08-20_21-13-00.db