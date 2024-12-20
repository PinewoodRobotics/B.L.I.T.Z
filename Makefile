export PYTHONPATH := $(shell pwd)

initiate-project:
	python -m venv .venv
	pip install -r requirements.txt
	pip install -e .

generate-proto: prepare
	protoc --python_out=project/generated --pyi_out=project/generated project/common/proto/*.proto

run-multiprocess-2-test:
	python project/test/april/april_tag_mlti_process_2.py

run-multiprocess:
	python project/test/april/april_tag_mult_process.py

run-april-server:
	cd project/recognition/position/april && python src/main.py

run-autobahn:
	nats-server -c project/autobahn/autobahn.conf

prepare:
	if [ ! -d "generated" ]; then mkdir generated; fi