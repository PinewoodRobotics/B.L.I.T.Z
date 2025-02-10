from pydantic import BaseModel


class AutobahnConfig(BaseModel):
    port: int
