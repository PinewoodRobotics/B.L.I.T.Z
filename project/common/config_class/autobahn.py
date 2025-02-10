from pydantic import BaseModel


class AutobahnConfig(BaseModel):
    host: str
    port: int
