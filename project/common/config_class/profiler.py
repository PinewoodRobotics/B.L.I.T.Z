from pydantic import BaseModel

from project.common.debug.logger import LogLevel


class LoggerConfig(BaseModel):
    enabled: bool
    profiler: "ProfilerConfig"
    level: LogLevel


class ProfilerConfig(BaseModel):
    activated: bool
    profile_functions: bool
    time_functions: bool
    output_file: str
