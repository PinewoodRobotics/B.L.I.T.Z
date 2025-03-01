#ifndef AUTOBAHN_H
#define AUTOBAHN_H

#include <iostream>
#include <string>
#include <unordered_map>
#include <functional>
#include <future>
#include <memory>
#include <thread>
#include <chrono>

#include <websocketpp/client.hpp>
#include <websocketpp/config/asio_client.hpp>
#include <boost/asio.hpp>

#include "autobahn/message.pb.h"

// Include Protobuf-generated headers

using namespace std::chrono_literals;

class Address
{
public:
  Address(std::string host, int port) : host(std::move(host)), port(port) {}

  std::string makeUrl() const
  {
    return "ws://" + host + ":" + std::to_string(port);
  }

private:
  std::string host;
  int port;
};

class Autobahn
{
public:
  explicit Autobahn(const Address &address)
      : address(address), isReconnecting(false), io_service(), ws_client(), work(io_service)
  {

    ws_client.init_asio(&io_service);

    ws_client.set_open_handler([this](websocketpp::connection_hdl hdl)
                               { onOpen(hdl); });

    ws_client.set_close_handler([this](websocketpp::connection_hdl hdl)
                                { onClose(hdl); });

    ws_client.set_message_handler([this](websocketpp::connection_hdl hdl, websocketpp::client<websocketpp::config::asio_client>::message_ptr msg)
                                  { onMessage(msg); });

    io_thread = std::thread([this]()
                            { io_service.run(); });
  }

  ~Autobahn()
  {
    io_service.stop();
    if (io_thread.joinable())
    {
      io_thread.join();
    }
  }

  std::future<void> begin()
  {
    return std::async(std::launch::async, [this]()
                      {
            try {
                websocketpp::lib::error_code ec;
                auto con = ws_client.get_connection(address.makeUrl(), ec);
                if (ec) {
                    throw std::runtime_error("Connection failed: " + ec.message());
                }
                ws_client.connect(con);
            } catch (const std::exception &e) {
                std::cerr << "Failed to connect: " << e.what() << std::endl;
                scheduleReconnect();
            } });
  }

  std::future<void> publish(const std::string &topic, const std::vector<uint8_t> &payload)
  {
    return std::async(std::launch::async, [this, topic, payload]()
                      {
            if (!ws_handle.lock()) {
                throw std::runtime_error("WebSocket not connected. Call begin() first.");
            }

            proto::autobahn::PublishMessage message;
            message.set_message_type(proto::autobahn::MessageType::PUBLISH);
            message.set_topic(topic);
            message.set_payload(payload.data(), payload.size());

            std::string serialized;
            if (!message.SerializeToString(&serialized)) {
                throw std::runtime_error("Failed to serialize PublishMessage.");
            }

            ws_client.send(ws_handle.lock(), serialized, websocketpp::frame::opcode::binary); });
  }

  std::future<void> subscribe(const std::string &topic, std::function<void(const std::vector<uint8_t> &)> callback)
  {
    return std::async(std::launch::async, [this, topic, callback]()
                      {
            if (!ws_handle.lock()) {
                throw std::runtime_error("WebSocket not connected. Call begin() first.");
            }
            callbacks[topic] = callback;

            proto::autobahn::TopicMessage message;
            message.set_message_type(proto::autobahn::MessageType::SUBSCRIBE);
            message.set_topic(topic);

            std::string serialized;
            if (!message.SerializeToString(&serialized)) {
                throw std::runtime_error("Failed to serialize TopicMessage.");
            }

            ws_client.send(ws_handle.lock(), serialized, websocketpp::frame::opcode::binary); });
  }

  std::future<void> unsubscribe(const std::string &topic)
  {
    return std::async(std::launch::async, [this, topic]()
                      {
            if (!ws_handle.lock()) {
                throw std::runtime_error("WebSocket not connected. Call begin() first.");
            }
            callbacks.erase(topic);

            proto::autobahn::UnsubscribeMessage message;
            message.set_message_type(proto::autobahn::MessageType::UNSUBSCRIBE);
            message.set_topic(topic);

            std::string serialized;
            if (!message.SerializeToString(&serialized)) {
                throw std::runtime_error("Failed to serialize UnsubscribeMessage.");
            }

            ws_client.send(ws_handle.lock(), serialized, websocketpp::frame::opcode::binary); });
  }

private:
  Address address;
  websocketpp::client<websocketpp::config::asio_client> ws_client;
  websocketpp::connection_hdl ws_handle;
  std::unordered_map<std::string, std::function<void(const std::vector<uint8_t> &)>> callbacks;
  bool isReconnecting;
  boost::asio::io_service io_service;
  boost::asio::io_service::work work;
  std::thread io_thread;

  void scheduleReconnect()
  {
    if (!isReconnecting)
    {
      isReconnecting = true;
      std::this_thread::sleep_for(5s);
      begin();
    }
  }

  void onOpen(websocketpp::connection_hdl hdl)
  {
    ws_handle = hdl; // This will work correctly now
    std::cout << "Connected to WebSocket server." << std::endl;
    isReconnecting = false;
  }

  void onClose(websocketpp::connection_hdl hdl)
  {
    std::cerr << "WebSocket connection closed." << std::endl;
    scheduleReconnect();
  }

  void onMessage(websocketpp::client<websocketpp::config::asio_client>::message_ptr msg)
  {
    proto::autobahn::PublishMessage messageProto;
    if (messageProto.ParseFromString(msg->get_payload()))
    {
      auto topic = messageProto.topic();
      if (callbacks.find(topic) != callbacks.end())
      {
        callbacks[topic](std::vector<uint8_t>(messageProto.payload().begin(), messageProto.payload().end()));
      }
    }
    else
    {
      std::cerr << "Failed to parse received message." << std::endl;
    }
  }
};

#endif // AUTOBAHN_H