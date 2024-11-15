initiate-project:
	python -m venv .venv
	pip install -r requirements.txt
	pip install -e .

generate-proto: prepare
	protoc --python_out=generated --pyi_out=generated common/proto/*.proto

run-multiprocess-2-test:
	python test/april/april_tag_mlti_process_2.py

run-april-server:
	python recognition/position/april/src/main.py

run-autobahn:
	nats-server -c autobahn/autobahn.conf

prepare:
	if [ ! -d "generated" ]; then mkdir generated; fi