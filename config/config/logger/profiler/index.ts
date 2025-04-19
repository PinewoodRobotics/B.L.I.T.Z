import { ProfilerConfig } from "../../../generated_schema/logger_types";

const profiler_config = new ProfilerConfig({
  activated: true,
  profile_functions: true,
  time_functions: true,
  output_file: "profiler.json",
});

export default profiler_config;
