import asyncio

from project.autobahn.autobahn_python.listener import Address, Listener


client = Listener(
    peer_addrs=[Address(host="localhost", port=8090)],
    addr=Address(host="localhost", port=8080),
)


async def main():
    asyncio.create_task(client.run())

    for i in range(100):
        await client.publish("test", f"Hello, world! {i}".encode())
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
