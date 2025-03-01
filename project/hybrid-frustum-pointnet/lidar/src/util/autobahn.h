#ifndef AUTOBAHN_H
#define AUTOBAHN_H

#include <atomic>
#include <boost/asio.hpp>
#include <boost/beast.hpp>
#include <boost/beast/websocket.hpp>
#include <functional>
#include <string>
#include <thread>
#include <unordered_map>

namespace asio = boost::asio;
namespace beast = boost::beast;
using tcp = asio::ip::tcp;
namespace websocket = beast::websocket;

// Enumeration for message flags
enum class Flags : uint8_t {
  SUBSCRIBE = 0x01,
  UNSUBSCRIBE = 0x02,
  PUBLISH = 0x03
};

class Autobahn {
 public:
  Autobahn(const std::string& host, const std::string& port);
  ~Autobahn();

  void begin();
  void subscribe(const std::string& topic,
                 std::function<void(const std::string&)> callback);
  void unsubscribe(const std::string& topic);
  void publish(const std::string& topic, const std::string& message);

 private:
  std::string host_;
  std::string port_;
  asio::io_context ioc_;
  tcp::resolver resolver_;
  websocket::stream<tcp::socket> ws_;
  std::unordered_map<std::string, std::function<void(const std::string&)>>
      subscriptions_;
  std::thread listening_thread_;
  std::atomic<bool> running_{true};

  void listen();
  void parse_message(const std::string& message);
  void send_message(Flags flag, const std::string& topic,
                    const std::string& message);
  void stop();
};

#endif  // AUTOBAHN_H