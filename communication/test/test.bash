#!bin/bash

python3 -m venv venv
source venv/bin/activate

python src/main.py & sleep 2 & curl -X POST http://127.0.0.1:5123/subscribe -H "Content-Type: application/json" -d '{"topic": "news", "post_url": "http://example.com/receive"}' & curl -X POST http://127.0.0.1:5123/post -H "Content-Type: application/json" -d '{"topic": "news", "data": {"message": "Hello, subscribers!"}}' & curl -X DELETE http://127.0.0.1:5123/unsubscribe -H "topic: news" -H "post_url: http://example.com/receive"