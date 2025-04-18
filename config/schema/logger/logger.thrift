include "../common/common.thrift"

namespace py thrift.logger

enum Level {
    DEBUG,
    INFO,
    WARNING,
    ERROR,
}

struct ProfilerConfig {
    1: required bool activated,
    2: required bool profile_functions,
    3: required bool time_functions,
    4: required string output_file,
}

struct LoggerConfig {
    1: required bool enabled,
    2: required ProfilerConfig profiler,
    3: required Level level,
}