import asyncio
from project.autobahn.autobahn_python.listener import Address, Listener


client = Listener(
    peer_addrs=[Address(host="localhost", port=8080)],
    addr=Address(host="localhost", port=8090),
)


async def callback(message: bytes):
    print(message.decode())


async def main():
    asyncio.create_task(client.run())
    await client.subscribe("test", callback)
    await asyncio.sleep(100)


if __name__ == "__main__":
    asyncio.run(main())
