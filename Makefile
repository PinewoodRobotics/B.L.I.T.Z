export PYTHONPATH := $(shell pwd)
ARGS ?=

initiate-project:
	python -m venv .venv
	pip install -r requirements.txt
	pip install -e .

run-multiprocess-2-test:
	python project/test/april/april_tag_mlti_process_2.py $(ARGS)

run-multiprocess:
	python project/test/april/april_tag_mult_process.py $(ARGS)

autobahn:
	cd project/autobahn/autobahn-rust && cargo run -- --config config.toml

ai-server:
	cd project/recognition/detection/image-recognition && python src/main.py $(ARGS)

april-server:
	python project/recognition/position/april/src/main.py $(ARGS)

prepare:
	if [ ! -d "generated" ]; then mkdir generated; fi

generate-proto-cpp-lidar:
	mkdir -p project/hybrid-frustum-pointnet/lidar/include/proto
	protoc -I=proto --cpp_out=project/hybrid-frustum-pointnet/lidar/include/proto $(shell find proto -name "*.proto")

generate-proto: prepare
	protoc -I=proto \
		--python_out=generated \
		--pyi_out=generated \
		$(shell find proto -name "*.proto")
	
	protol --create-package --in-place --python-out generated protoc --proto-path=proto/ $(shell find proto -name "*.proto")

position-extrapolator:
	python project/pos_extrapolator/src/main.py $(ARGS)

watchdog:
	python project/watchdog/src/main.py

flash:
	./scripts/flash.bash $(ARGS)

check-all:
	ruff check .

check-project:
	ruff check project/

run-config-ts:
	npx tsx config/ $(ARGS)
