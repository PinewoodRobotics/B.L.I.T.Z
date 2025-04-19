export PYTHONPATH := $(shell pwd)
ARGS ?=

VENV_PYTHON := .venv/bin/python

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
	if [ ! -d "generated" ]; then mkdir generated; fi

generate-proto-cpp-lidar:
	mkdir -p project/hybrid-frustum-pointnet/lidar/include/proto
	protoc -I=proto --cpp_out=project/hybrid-frustum-pointnet/lidar/include/proto$(find proto -name "*.proto")

generate-proto: prepare
	mkdir -p generated/proto
	protoc -I=proto \
		--python_out=generated/proto \
		$(shell find proto -name "*.proto")
	
	.venv/bin/protol --create-package --in-place --python-out generated/proto protoc --proto-path=proto/ $(shell find proto -name "*.proto")

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
	npx tsx config/ $(ARGS)

send-to-target:
	rsync -av --progress --exclude-from=.gitignore --delete ./ ubuntu@10.47.65.$(ARGS):~/Documents/B.L.I.T.Z/

test:
	pytest project

THRIFT_DIR = config/schema
SCHEMA_DIR = config/generated_schema
GEN_DIR = generated

thrift-to-py:
	mkdir -p $(GEN_DIR)
	thrift -r --gen py:package_prefix=generated. \
	  -I $(THRIFT_DIR) \
	  -out $(GEN_DIR) \
	  $(THRIFT_DIR)/config.thrift

	stubgen -o $(GEN_DIR) .

thrift-to-ts:
	mkdir -p $(SCHEMA_DIR)
	thrift-ts $(THRIFT_DIR) -o $(SCHEMA_DIR)

thrift: thrift-to-py thrift-to-ts