from pydantic import BaseModel


class ProfilerConfig(BaseModel):
    activated: bool
    profile_function: bool
    time_function: bool
    output_file: str
