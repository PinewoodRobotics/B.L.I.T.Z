import asyncio
from project.autobahn.autobahn_python.autobahn import Autobahn


autobahn = Autobahn(host="localhost", port=8080)


async def callback(message: bytes):
    print(message.decode())


async def main():
    await autobahn.begin()
    await autobahn.subscribe("test", callback)
    await asyncio.sleep(2)
    print("Unsubscribing")
    await autobahn.unsubscribe("test")
    await asyncio.sleep(100)


if __name__ == "__main__":
    asyncio.run(main())
