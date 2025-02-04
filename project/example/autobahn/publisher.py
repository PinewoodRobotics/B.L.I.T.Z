import asyncio

from project.autobahn.autobahn_python.autobahn import Autobahn


autobahn = Autobahn(host="localhost", port=8080)


async def main():
    await autobahn.begin()
    for i in range(100):
        await autobahn.publish("test", f"Hello, world! {i}".encode())
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
