import toml
import zmq
from config import Config

if __name__ == "__main__":
    # Load configuration
    config = toml.load(open("config.toml"))
    if "main-config-path" in config:
        config = toml.load(open(config["main-config-path"]))
    config = Config(config)

    context = zmq.Context()

    # Internal PUB socket for publishing within the internal network
    internal_pub_socket = context.socket(zmq.PUB)
    internal_pub_socket.bind(f"tcp://*:{config.internal_pub_port}")

    # Internal SUB socket for receiving messages from internal publishers
    internal_sub_socket = context.socket(zmq.SUB)
    internal_sub_socket.bind(f"tcp://*:{config.internal_sub_port}")
    internal_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all topics

    # External PUB socket for publishing to external peers
    external_pub_socket = context.socket(zmq.PUB)
    external_pub_socket.bind(f"tcp://*:{config.self_port}")

    # External SUB socket for receiving messages from external peers
    external_sub_socket = context.socket(zmq.SUB)
    for peer in config.peers:
        external_sub_socket.connect(f"tcp://{peer}")
    external_sub_socket.setsockopt_string(
        zmq.SUBSCRIBE, ""
    )  # Subscribe to all external messages

    # Poller to check for incoming messages on internal and external sub sockets
    poller = zmq.Poller()
    poller.register(internal_sub_socket, zmq.POLLIN)
    poller.register(external_sub_socket, zmq.POLLIN)

    print(
        f"Broker started with internal PUB on port {config.internal_pub_port}, "
        f"internal SUB on port {config.internal_sub_port}, "
        f"and external PUB on port {config.self_port}"
    )

    while True:
        socks = dict(poller.poll())

        # Check for messages from internal publishers
        if internal_sub_socket in socks:
            msg = internal_sub_socket.recv_string()
            # Forward the message to all internal subscribers
            internal_pub_socket.send_string(msg)

            # If the message is intended for external distribution, send it out
            if msg.startswith("EXTERNAL"):
                external_pub_socket.send_string(msg[10:])  # Strips "EXTERNAL" prefix

        # Check for messages from external peers
        if external_sub_socket in socks:
            msg = external_sub_socket.recv_string()
            # Forward the message to internal subscribers
            internal_pub_socket.send_string(msg)
