include "../common/common.thrift"

namespace py thrift.watchdog

struct WatchdogConfig {
    1: required bool send_stats,
    2: required i32 stats_interval_seconds,
    3: required string stats_publish_topic,
    4: required string confirmation_topic,
}