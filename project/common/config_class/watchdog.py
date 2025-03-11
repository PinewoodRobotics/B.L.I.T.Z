from pydantic import BaseModel


class WatchdogConfig(BaseModel):
    send_stats: bool
    stats_interval_seconds: int
    stats_publish_topic: str
