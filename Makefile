export PYTHONPATH := $(shell pwd)
ARGS ?=

VENV_PYTHON := .venv/bin/python

THRIFT_DIR = ThriftTsConfig/schema
THRIFT_ROOT_FILE = $(THRIFT_DIR)/config.thrift
PROTO_DIR = src/proto

GEN_DIR = src/blitz/generated
PROTO_GEN_DIR = $(GEN_DIR)/proto
THRIFT_GEN_DIR = $(GEN_DIR)/thrift

THRIFT_TS_SCHEMA_GEN_DIR = $(THRIFT_GEN_DIR)/ts_schema
PROTO_PY_GEN_DIR = $(PROTO_GEN_DIR)/python

initiate-project:
	if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip install -e .

mac-deps:
	brew install sshpass

ai-server:
	cd project/recognition/detection/image-recognition && $(VENV_PYTHON) src/main.py $(ARGS)
	
april-server:
	$(VENV_PYTHON) -u src/blitz/recognition/position/april/src/main.py $(ARGS)

lidar-reader-2d:
	$(VENV_PYTHON) src/blitz/lidar/lidar_2d/main.py $(ARGS)

lidar-point-processor:
	$(VENV_PYTHON) src/blitz/lidar/lidar_point_processor/main.py $(ARGS)

lidar-3d:
	@if [ -f "target/release/lidar-3d" ]; then target/release/lidar-3d $(ARGS); else echo "Lidar 3D is not built, run 'make build-lidar-3d'"; fi

build-lidar-3d:
	cd src/blitz/rust/lidar_3d && cargo build --release

prepare:
	mkdir -p $(GEN_DIR)
	touch $(GEN_DIR)/__init__.py
	mkdir -p $(PROTO_GEN_DIR)
	touch $(PROTO_GEN_DIR)/__init__.py
	mkdir -p $(THRIFT_GEN_DIR)
	touch $(THRIFT_GEN_DIR)/__init__.py

generate-proto-cpp-lidar:
	mkdir -p project/hybrid-frustum-pointnet/lidar/include/proto
	protoc -I=$(PROTO_DIR) --cpp_out=project/hybrid-frustum-pointnet/lidar/include/proto $(shell find $(PROTO_DIR) -name "*.proto")

generate-proto-python: prepare
	mkdir -p $(PROTO_PY_GEN_DIR)
	protoc -I=$(PROTO_DIR) \
		--python_out=$(PROTO_PY_GEN_DIR) \
		--pyi_out=$(PROTO_PY_GEN_DIR) \
		$(shell find $(PROTO_DIR) -name "*.proto")
	.venv/bin/fix-protobuf-imports $(PROTO_PY_GEN_DIR)


position-extrapolator:
	$(VENV_PYTHON) -u src/blitz/pos_extrapolator/main.py $(ARGS)

watchdog:
	$(VENV_PYTHON) -u src/blitz/watchdog/main.py

flash:
	./scripts/flash.bash $(ARGS)

check-all:
	ruff check .

check-project:
	ruff check project/

run-config-ts:
	npm run config

send-to-target:
	rsync -av --progress --exclude-from=.gitignore --delete ./ ubuntu@10.47.65.7:~/Documents/B.L.I.T.Z/

test:
	$(VENV_PYTHON) -m pytest

test-coverage:
	coverage run --source=src/blitz/ -m pytest
	coverage report
	coverage html

thrift-to-py:
	mkdir -p $(THRIFT_GEN_DIR)
	thrift -r --gen py:enum,type_hints,package_prefix=blitz.generated.thrift. \
	  	-I $(THRIFT_DIR) \
	  	-out $(THRIFT_GEN_DIR) \
	  	$(THRIFT_ROOT_FILE)

thrift-to-ts:
	@if [ "$$(uname)" = "Linux" ]; then \
		echo "Skipping thrift-to-ts on Linux"; \
	else \
		mkdir -p $(THRIFT_TS_SCHEMA_GEN_DIR); \
		npm run generate-thrift; \
	fi

thrift: thrift-to-py thrift-to-ts

generate: prepare thrift generate-proto-python

deploy:
	$(VENV_PYTHON) -u scripts/deploy.py

download-replays:
	@echo "Downloading replay file from remote server..."
	scp ubuntu@10.47.65.7:~/Documents/B.L.I.T.Z/replay-2025-08-20_21-13-00.db ./replay-2025-08-20_21-13-00.db