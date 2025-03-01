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
	cd project/autobahn/autobahn-rust && cargo run -- --config config.toml

ai-server:
	cd project/recognition/detection/image-recognition && python src/main.py

april-server:
	python project/recognition/position/april/src/main.py

prepare:
	if [ ! -d "generated" ]; then mkdir generated; fi

position-extrapolator:
	cd project/recognition/position/pos_extrapolator/ && python src/main.py

generate-proto-lidar:
	mkdir -p project/hybrid-frustum-pointnet/lidar/include/proto
	protoc --cpp_out=project/hybrid-frustum-pointnet/lidar/include/proto project/common/proto/*.proto
