import asyncio
from typing import Awaitable, Callable

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.autobahn.autobahn_python.util import Address

CONFIG_PATH = "config/"


async def check_autobahn_connection(
    autobahn_server: Autobahn, config_input: Callable[[bytes], Awaitable[None]]
):
    connected = False
    while not connected:
        try:
            await autobahn_server.begin()
            connected = True
        except Exception as e:
            print(f"Error connecting to Autobahn: {str(e)}")
            await asyncio.sleep(1)
    print("Autobahn connected")

    await autobahn_server.subscribe("config", config_input)


async def main():
    autobahn_server = Autobahn(Address("localhost", 8080))

    async def config_input(data: bytes):
        config_str = data.decode("utf-8")
        with open(CONFIG_PATH + "config.json", "w") as f:
            f.write(config_str)

    await check_autobahn_connection(autobahn_server, config_input)

    while True:
        try:
            await autobahn_server.ping()
        except Exception as e:
            print(f"Error pinging Autobahn: {str(e)}")
            await check_autobahn_connection(autobahn_server, config_input)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
