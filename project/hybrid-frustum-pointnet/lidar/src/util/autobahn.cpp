#include "autobahn.h"

#include <iostream>
#include <stdexcept>

Autobahn::Autobahn(const std::string& host, const std::string& port)
    : host_(host), port_(port), resolver_(ioc_), ws_(ioc_) {}

Autobahn::~Autobahn() {
  stop();
  if (listening_thread_.joinable()) {
    listening_thread_.join();
  }
}

void Autobahn::begin() {
  // Resolve the hostname
  auto const results = resolver_.resolve(host_, port_);

  // Connect to the resolved endpoint
  asio::connect(ws_.next_layer(), results.begin(), results.end());

  // Perform the WebSocket handshake
  ws_.handshake(host_, "/");

  // Start the listening thread
  listening_thread_ = std::thread([this]() { listen(); });
}

void Autobahn::subscribe(const std::string& topic,
                         std::function<void(const std::string&)> callback) {
  subscriptions_[topic] = callback;
  send_message(Flags::SUBSCRIBE, topic, "");
}

void Autobahn::unsubscribe(const std::string& topic) {
  subscriptions_.erase(topic);
  send_message(Flags::UNSUBSCRIBE, topic, "");
}

void Autobahn::publish(const std::string& topic, const std::string& message) {
  send_message(Flags::PUBLISH, topic, message);
}

void Autobahn::listen() {
  try {
    while (running_) {
      beast::flat_buffer buffer;
      ws_.read(buffer);

      auto data = beast::buffers_to_string(buffer.data());
      parse_message(data);
    }
  } catch (const std::exception& e) {
    std::cerr << "Error in listener: " << e.what() << std::endl;
  }
}

void Autobahn::parse_message(const std::string& message) {
  try {
    auto it = message.begin();

    // Read flag
    Flags flag = static_cast<Flags>(*it++);

    // Read topic length
    uint16_t topic_length =
        static_cast<uint8_t>(*it++) << 8 | static_cast<uint8_t>(*it++);

    // Read topic
    std::string topic(it, it + topic_length);
    it += topic_length;

    // Read payload
    std::string payload(it, message.end());

    if (flag == Flags::PUBLISH) {
      for (const auto& [subscription_topic, callback] : subscriptions_) {
        if (topic.compare(0, subscription_topic.size(), subscription_topic) ==
            0) {
          callback(payload);
        }
      }
    }
  } catch (const std::exception& e) {
    std::cerr << "Error parsing message: " << e.what() << std::endl;
  }
}

void Autobahn::send_message(Flags flag, const std::string& topic,
                            const std::string& message) {
  try {
    // Create a binary buffer
    std::vector<uint8_t> buffer;

    // Add the flag (1 byte)
    buffer.push_back(static_cast<uint8_t>(flag));

    // Add the topic length (4 bytes, big-endian)
    uint32_t topic_length = topic.size();
    buffer.push_back(static_cast<uint8_t>((topic_length >> 24) & 0xFF));
    buffer.push_back(static_cast<uint8_t>((topic_length >> 16) & 0xFF));
    buffer.push_back(static_cast<uint8_t>((topic_length >> 8) & 0xFF));
    buffer.push_back(static_cast<uint8_t>(topic_length & 0xFF));

    // Add the topic (variable length)
    buffer.insert(buffer.end(), topic.begin(), topic.end());

    // Add the payload length (4 bytes, big-endian)
    uint32_t message_length = message.size();
    buffer.push_back(static_cast<uint8_t>((message_length >> 24) & 0xFF));
    buffer.push_back(static_cast<uint8_t>((message_length >> 16) & 0xFF));
    buffer.push_back(static_cast<uint8_t>((message_length >> 8) & 0xFF));
    buffer.push_back(static_cast<uint8_t>(message_length & 0xFF));

    // Add the payload (variable length)
    buffer.insert(buffer.end(), message.begin(), message.end());

    // Set WebSocket to binary mode
    ws_.binary(true);

    // Send the buffer directly as binary
    ws_.write(asio::buffer(buffer));
  } catch (const std::exception& e) {
    std::cerr << "Error sending message: " << e.what() << std::endl;
  }
}

void Autobahn::stop() {
  running_ = false;
  ws_.close(websocket::close_code::normal);
}