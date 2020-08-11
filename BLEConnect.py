from bleak import BleakClient, discover
import asyncio

address = ''
tempUUID = (
    "15005991-b131-3396-014c-664c9867b917"
)


def callback(sender,data):
    print(f"{sender}: {data}")


async def run():
    devices = await discover()
    for d in devices:
        print(d)
        if d.name == 'GUTRUF LAB v0.01':
            address = d.address
            print('Device found.')
            async with BleakClient(address, loop=loop) as client:
                services = await client.get_services()
                for s in services:
                    for char in s.characteristics:
                        print(f'Characteristic: {char}')
                        print(f'[{char.uuid}] {char.description}: {char.descriptors}, {char.handle}, {char.properties}')
                # await client.start_notify(tempUUID, callback)

loop = asyncio.get_event_loop()
loop.run_until_complete(run())