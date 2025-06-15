import {
  Level,
  LoggerConfig,
} from "../../../blitz/generated/thrift/ts_schema/logger_types";
import profiler_config from "./profiler";

const logger: LoggerConfig = {
  enabled: false,
  level: Level.DEBUG,
  profiler: profiler_config,
};

export default logger;
