import argparse
import asyncio
from enum import Enum

from blitz.common.autobahn_python.autobahn import Autobahn
from blitz.common.autobahn_python.util import Address
from blitz.generated.proto.python.WatchDogMessage_pb2 import ProcessType, StartupMessage


def from_string_to_process_type(string: str) -> ProcessType:
    for process_type in ProcessType.DESCRIPTOR.values:
        if process_type.name == string.upper():
            return process_type
    raise ValueError(f"Invalid process type: {string}")


async def main():
    autobahn_server = Autobahn(Address("localhost", 8080))
    await autobahn_server.begin()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "start",
        type=str,
        nargs="*",
        help="Start a process (e.g. 'blitz start lidar_reader_2d')",
    )
    parser.add_argument(
        "stop",
        type=str,
        nargs="*",
        help="Stop a process (e.g. 'blitz stop lidar_reader_2d')",
    )
    args = parser.parse_args()

    if args.start:
        process_type = from_string_to_process_type(args.start[0])
        await autobahn_server.publish(
            "watchdog/start",
            StartupMessage(
                py_tasks=[process_type], abort_previous=False
            ).SerializeToString(),
        )
    elif args.stop:
        for process_type in args.stop:
            process_type = from_string_to_process_type(process_type)
            print(process_type)
    else:
        print("Invalid command")


if __name__ == "__main__":
    asyncio.run(main())
