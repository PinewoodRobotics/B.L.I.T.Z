import asyncio
import time
from autobahn_client.client import Autobahn
import psutil
from watchdog.util.logger import stats, info
import watchdog.util.logger as logger_module
from generated.PiStatus_pb2 import (
    PiProcess,
    PiStatus,
    Ping,
    Pong,
    StatusType,
)
from util.system import (
    BasicSystemConfig,
    get_camera_ports_in_use,
    get_system_name,
    get_top_10_processes,
)


def _collect_system_stats():
    cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
    cpu_usage_total = (
        sum(cpu_per_core) / len(cpu_per_core) if cpu_per_core else psutil.cpu_percent()
    )
    memory = psutil.virtual_memory()
    disk_info = psutil.disk_usage("/")
    net_info = psutil.net_io_counters()
    top_10_processes = get_top_10_processes()
    ports_in_use = get_camera_ports_in_use()
    return (
        cpu_per_core,
        cpu_usage_total,
        memory,
        disk_info,
        net_info,
        top_10_processes,
        ports_in_use,
    )


async def process_watcher(config: BasicSystemConfig | None):
    print(
        f"[DEBUG] Process watcher running! autobahn_instance={logger_module.autobahn_instance is not None}, PREFIX={logger_module.PREFIX}"
    )
    while True:
        if config and config.watchdog.send_stats:
            (
                cpu_per_core,
                cpu_usage_total,
                memory,
                disk_info,
                net_info,
                top_10_processes,
                ports_in_use,
            ) = await asyncio.to_thread(_collect_system_stats)
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
                ports_in_use=ports_in_use,
            )

            await stats(pi_status.SerializeToString())

        await asyncio.sleep(
            config.watchdog.stats_pub_period_s
            if config and config.watchdog.send_stats
            else 1
        )


async def setup_ping_pong(autobahn_server: Autobahn, system_name: str):
    async def ping_server(data: bytes):
        ping = Ping.FromString(data)
        pong = Pong(
            pi_name=system_name,
            timestamp_ms_received=int(time.time() * 1000),
            timestamp_ms_original=int(ping.timestamp),
        )

        await autobahn_server.publish("pi-pong", pong.SerializeToString())

    await autobahn_server.subscribe("pi-ping", ping_server)
