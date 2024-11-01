import argparse
from flask import Flask, request
import requests

app = Flask(__name__)
post_sub_data_urls = {}
log = False


@app.route("/post", methods=["POST"])
def post_listener():
    """
    A way for the client to send data to other subscribed clients.
    """
    data = request.json
    topic = data.get("topic")
    message = data.get("data")

    if log:
        print("Post")
        print("Topic:", topic)
        print("Message:", message)

    if topic in post_sub_data_urls:
        for url in post_sub_data_urls[topic]:
            requests.post(url, json=message)

    return "OK", 200


@app.route("/subscribe", methods=["POST"])
def subscribe_listener():
    """
    Allows a client to subscribe to a topic.
    """
    data = request.json
    topic = data.get("topic")
    post_url = data.get("post_url")

    if log:
        print("Subscribe")
        print("Topic:", topic)
        print("Post URL:", post_url)

    if topic not in post_sub_data_urls:
        post_sub_data_urls[topic] = []

    post_sub_data_urls[topic].append(post_url)

    return "OK", 200


@app.route("/unsubscribe", methods=["DELETE"])
def unsubscribe_listener():
    """
    Allows a client to unsubscribe from a topic.
    """
    topic = request.headers.get("topic")
    post_url = request.headers.get("post_url")

    if log:
        print("Unsubscribe")
        print("Topic:", topic)
        print("Post URL:", post_url)

    if topic in post_sub_data_urls and post_url in post_sub_data_urls[topic]:
        post_sub_data_urls[topic].remove(post_url)

    return "OK", 200


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A script that demonstrates argument parsing."
    )

    parser.add_argument("--port", type=str, help="An example argument.", required=False)
    parser.add_argument(
        "--log", type=str, help="Path to the configuration file.", required=False
    )

    args = parser.parse_args()

    if args.log is not None and args.log.lower() == "true":
        print("Logging enabled!")
        log = True

    app.run(host="127.0.0.1", port=1234 if args.port is None else args.port)
