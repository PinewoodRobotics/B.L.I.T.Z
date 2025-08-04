import argparse
import asyncio
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich import print as rprint

import requests

from blitz.common.util.system import ProcessType, load_basic_system_config


def from_string_to_process_type(string: str) -> ProcessType:
    for process_type in ProcessType:
        if process_type.value == string:
            return process_type
    raise ValueError(f"Invalid process type: {string}")


async def main():
    global_config = load_basic_system_config()
    console = Console()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        type=str,
        choices=["start", "stop", "status", "restart"],
        help="Command to execute (start/stop/status/restart)",
    )
    parser.add_argument(
        "process",
        type=str,
        nargs="*",
        help="Process name(s) to operate on",
    )
    args = parser.parse_args()

    if args.command == "start" and args.process:
        try:
            process_type = from_string_to_process_type(args.process[0])
            response = requests.post(
                f"http://{global_config.watchdog.host}:{global_config.watchdog.port}/start/process",
                json={"process_types": [process_type.value]},
            )
            if response.status_code == 200:
                console.print(f"[green]Successfully started {args.process[0]}[/green]")
            else:
                console.print(
                    f"[red]Failed to start {args.process[0]}: {response.json()}[/red]"
                )
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
        except requests.exceptions.ConnectionError:
            console.print(
                f"[red]Error: Could not connect to watchdog server at {global_config.watchdog.host}:{global_config.watchdog.port}[/red]"
            )
    elif args.command == "stop" and args.process:
        for process_name in args.process:
            try:
                process_type = from_string_to_process_type(process_name)
                response = requests.post(
                    f"http://{global_config.watchdog.host}:{global_config.watchdog.port}/stop/process",
                    json={"process_types": [process_type.value]},
                )
                if response.status_code == 200:
                    console.print(f"[green]Successfully stopped {process_name}[/green]")
                else:
                    console.print(
                        f"[red]Failed to stop {process_name}: {response.text}[/red]"
                    )
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
            except requests.exceptions.ConnectionError:
                console.print(
                    f"[red]Error: Could not connect to watchdog server at {global_config.watchdog.host}:{global_config.watchdog.port}[/red]"
                )
    elif args.command == "status":
        try:
            response = requests.get(
                f"http://{global_config.watchdog.host}:{global_config.watchdog.port}/get/system/status",
            )
            data = response.json()

            table = Table(title="System Status")
            table.add_column("System", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Active Processes", style="yellow")
            table.add_column("Config Set", style="magenta")

            active_processes = (
                ", ".join(data["active_processes"])
                if data["active_processes"]
                else "None"
            )
            table.add_row(
                data["system_info"],
                data["status"],
                active_processes,
                "Yes" if data["config_set"] else "No",
            )

            console.print(table)
        except requests.exceptions.ConnectionError:
            console.print(
                f"[red]Error: Could not connect to watchdog server at {global_config.watchdog.host}:{global_config.watchdog.port}[/red]"
            )
    elif args.command == "restart" and args.process:
        for process_name in args.process:
            try:
                process_type = from_string_to_process_type(process_name)
                stop_response = requests.post(
                    f"http://{global_config.watchdog.host}:{global_config.watchdog.port}/stop/process",
                    json={"process_types": [process_type.value]},
                )
                if stop_response.status_code == 200:
                    console.print(f"[green]Successfully stopped {process_name}[/green]")
                    start_response = requests.post(
                        f"http://{global_config.watchdog.host}:{global_config.watchdog.port}/start/process",
                        json={"process_types": [process_type.value]},
                    )
                    if start_response.status_code == 200:
                        console.print(
                            f"[green]Successfully restarted {process_name}[/green]"
                        )
                    else:
                        console.print(
                            f"[red]Failed to restart {process_name}: {start_response.text}[/red]"
                        )
                else:
                    console.print(
                        f"[red]Failed to stop {process_name}: {stop_response.text}[/red]"
                    )
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
            except requests.exceptions.ConnectionError:
                console.print(
                    f"[red]Error: Could not connect to watchdog server at {global_config.watchdog.host}:{global_config.watchdog.port}[/red]"
                )
    else:
        console.print("[red]Invalid command or missing process name[/red]")


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
