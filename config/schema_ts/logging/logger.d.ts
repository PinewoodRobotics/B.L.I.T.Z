import { ProfilerConfig } from "./profiler";

export interface LoggerConfig {
  enabled: boolean;
  profiler: ProfilerConfig;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
}
