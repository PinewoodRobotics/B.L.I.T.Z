import asyncio
import psutil
from blitz.generated.proto.status.PiStatus_pb2 import PiProcess, PiStatus
from blitz.generated.thrift.ttypes import Config
from blitz.common.autobahn_python.autobahn import Autobahn
from blitz.common.util.system import get_system_name, get_top_10_processes


async def process_watcher(config: Config | None, autobahn_server: Autobahn):
    while True:
        if config and config.watchdog.send_stats:
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            cpu_usage_total = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_info = psutil.disk_usage("/")
            net_info = psutil.net_io_counters()
            top_10_processes = get_top_10_processes()
            pi_status = PiStatus(
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

            await autobahn_server.publish(
                config.watchdog.stats_publish_topic,
                pi_status.SerializeToString(),
            )

        await asyncio.sleep(
            config.watchdog.stats_interval_seconds
            if config and config.watchdog.send_stats
            else 1
        )
