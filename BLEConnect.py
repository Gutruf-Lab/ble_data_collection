from bleak import BleakClient, discover
import asyncio


def notification_handler(sender, data):
    """Simple notification handler which prints the data received."""
    print("{0}: {1}".format(handle_desc_pairs[sender], int.from_bytes(data, byteorder='little')))


async def run():
    address = ''
    while address == '':
        devices = await discover(timeout=2)
        for d in devices:
            print(d)
            if d.name == 'GUTRUF LAB v0.01':
                address = d.address
                print('Device found.')
        print('----')

    async with BleakClient(address, loop=loop) as client:
        x = await client.is_connected()
        services = await client.get_services()
        for s in services:
            for char in s.characteristics:
                # print(f'Characteristic: {char}')
                print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')
                handle_desc_pairs[char.handle] = char.description

        await client.start_notify('15005991-b131-3396-014c-664c9867b917', notification_handler)
        await client.start_notify('6eb675ab-8bd1-1b9a-7444-621e52ec6823', notification_handler)

        while True:
            await asyncio.sleep(5.0)

if __name__ == "__main__":
    global handle_desc_pairs
    handle_desc_pairs = {}
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())