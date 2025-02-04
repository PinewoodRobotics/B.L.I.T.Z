export PYTHONPATH := $(shell pwd)

initiate-project:
	python -m venv .venv
	pip install -r requirements.txt
	pip install -e .

run-multiprocess-2-test:
	python project/test/april/april_tag_mlti_process_2.py

run-multiprocess:
	python project/test/april/april_tag_mult_process.py

autobahn:
	cd project/autobahn/autobahn-rust && cargo run

ai-server:
	cd project/recognition/detection/image-recognition && python src/main.py

april-server:
	(cd project/recognition/position/april && python src/main.py)

prepare:
	if [ ! -d "generated" ]; then mkdir generated; fi

generate-proto-cpp-navx2:
	mkdir -p project/hardware/navx2/include/proto
	protoc --cpp_out=project/hardware/navx2/include/proto project/common/proto/*.proto

generate-proto: prepare
	protoc -I=proto \
		--python_out=generated \
		--pyi_out=generated \
		$(shell find proto -name "*.proto")
	
	protol --create-package --in-place --python-out generated protoc --proto-path=proto/ $(shell find proto -name "*.proto")

position-extrapolator:
	cd project/recognition/position/pos_extrapolator/ && python src/main.py

check-all:
	ruff check .

check-project:
	ruff check project/
