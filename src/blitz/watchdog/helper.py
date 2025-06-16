import asyncio
from enum import Enum
import psutil
from blitz.common.debug.logger import error, stats, success
from blitz.generated.proto.python.status.PiStatus_pb2 import (
    PiProcess,
    PiStatus,
    StatusType,
)
from blitz.generated.thrift.config.ttypes import Config
from blitz.common.autobahn_python.autobahn import Autobahn
from blitz.common.util.system import (
    BasicSystemConfig,
    get_system_name,
    get_top_10_processes,
)


class ProcessType(Enum):
    POS_EXTRAPOLATOR = "position-extrapolator"
    LIDAR_READER_2D = "lidar-reader-2d"
    LIDAR_POINT_PROCESSOR = "lidar-point-processor"
    LIDAR_PROCESSING = "lidar-processing"
    CAMERA_PROCESSING = "april-server"


async def process_watcher(config: BasicSystemConfig | None):
    while True:
        if config and config.watchdog.send_stats:
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            cpu_usage_total = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_info = psutil.disk_usage("/")
            net_info = psutil.net_io_counters()
            top_10_processes = get_top_10_processes()
            pi_status = PiStatus(
                type=StatusType.SYSTEM_STATUS,
                pi_name=get_system_name(),
                cpu_usage_cores=cpu_per_core,
                cpu_usage_total=cpu_usage_total,
                memory_usage=memory.percent,
                disk_usage=disk_info.percent,
                net_usage_in=net_info.bytes_recv,
                net_usage_out=net_info.bytes_sent,
                top_10_processes=[
                    PiProcess(
                        name=process.name(),
                        pid=process.pid,
                        cpu_usage=process.cpu_percent(),
                    )
                    for process in top_10_processes
                ],
            )

            await stats(pi_status.SerializeToString())

        await asyncio.sleep(
            config.watchdog.stats_pub_period_s
            if config and config.watchdog.send_stats
            else 1
        )
