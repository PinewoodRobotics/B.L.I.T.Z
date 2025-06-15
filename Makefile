export PYTHONPATH := $(shell pwd)
ARGS ?=

VENV_PYTHON := .venv/bin/python

THRIFT_DIR = src/config/schema
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

ai-server:
	cd project/recognition/detection/image-recognition && $(VENV_PYTHON) src/main.py $(ARGS)
	
april-server:
	$(VENV_PYTHON) -u project/recognition/position/april/src/main.py $(ARGS)

lidar-reader-2d:
	$(VENV_PYTHON) project/lidar/lidar_2d/main.py $(ARGS)

lidar-point-processor:
	$(VENV_PYTHON) project/lidar/lidar_point_processor/main.py $(ARGS)

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
	
	if [ -f .venv/bin/protol ]; then \
		.venv/bin/protol --create-package --in-place --python-out $(PROTO_GEN_DIR) protoc --proto-path=$(PROTO_DIR)/ $(shell find $(PROTO_DIR) -name "*.proto"); \
	else \
		echo "protol not found, skipping package creation (install with: pip install protol)"; \
	fi

position-extrapolator:
	$(VENV_PYTHON) -u project/pos_extrapolator/src/main.py $(ARGS)

watchdog:
	$(VENV_PYTHON) -u project/watchdog/main.py

flash:
	./scripts/flash.bash $(ARGS)

check-all:
	ruff check .

check-project:
	ruff check project/

run-config-ts:
	npm run config

send-to-target:
	rsync -av --progress --exclude-from=.gitignore --delete ./ ubuntu@10.47.65.$(ARGS):~/Documents/B.L.I.T.Z/

test:
	pytest

thrift-to-py:
	mkdir -p $(THRIFT_GEN_DIR)
	thrift -r --gen py:enum,type_hints,package_prefix=blitz.generated.thrift. \
	  	-I $(THRIFT_DIR) \
	  	-out $(THRIFT_GEN_DIR) \
	  	$(THRIFT_ROOT_FILE)

thrift-to-ts:
	mkdir -p $(THRIFT_TS_SCHEMA_GEN_DIR)
	thrift-ts $(THRIFT_DIR) -o $(THRIFT_TS_SCHEMA_GEN_DIR)

thrift: thrift-to-py thrift-to-ts

generate: prepare thrift generate-proto-python