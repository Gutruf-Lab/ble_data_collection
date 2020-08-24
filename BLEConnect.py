from bleak import BleakClient, discover
import asyncio
import pandas as pd
import os
from os import path
import datetime
from datetime import timedelta
from collections import defaultdict

from bleak.exc import BleakDotNetTaskError, BleakError

new_data = defaultdict(lambda: "Not found")

# Time in milliseconds (!)
storage_timing = 750


def notification_handler(sender, data):
    outgoing_data = pd.DataFrame()
    read_data = pd.DataFrame()
    global new_data

    if len(new_data.keys()) < 2:
        new_data["Time:"] = [datetime.datetime.now()]

    if handle_desc_pairs[sender] == "Temp Value:":
        if new_data[handle_desc_pairs[sender]] == "Not found":
            new_data[handle_desc_pairs[sender]] = [int.from_bytes(data, byteorder='little')]
    else:
        if new_data["Temp Value:"] != "Not found":
            new_data[handle_desc_pairs[sender]] = [int.from_bytes(data, byteorder='little')]

    # print("\nTime {0}. Dif: {1}\n".format(datetime.datetime.now(), datetime.datetime.now() - new_data["Time:"][0]))
    if len(new_data.keys()) > 2:
        if datetime.datetime.now() - timedelta(milliseconds=storage_timing) >= new_data["Time:"][0]:
            new_df = pd.DataFrame(new_data)
            print(new_df)

            new_df.to_csv('data/streamed_data.csv',
                                 index=False,
                                 header=False,
                                 mode='a'  # append data to csv file
                                 )
            new_data["Time:"] = [datetime.datetime.now()]
            del new_data["Temp Value:"]
            del new_data["Strain Value:"]


async def run(event_loop):
    while True:
        address = ''
        try:
            while address == '':
                devices = await discover(timeout=1)
                for d in devices:
                    print(d)
                    if d.name == 'GUTRUF LAB v0.01':
                        address = d.address
                        print('Device found.')
                print('----')

            async with BleakClient(address, loop=event_loop) as client:
                x = await client.is_connected()
                # disconnected_event = asyncio.Event()
                # async def disconnect_callback(client, future):
                #     print("Disconnected callback called!")
                #     loop.call_soon_threadsafe(disconnected_event.set)
                #     print("Connection lost. Returning to BLE device search.")
                #     client.stop_notify('15005991-b131-3396-014c-664c9867b917')
                #     client.stop_notify('6eb675ab-8bd1-1b9a-7444-621e52ec6823')
                #     await disconnected_event.wait()
                #     print("Connected: {0}".format(await client.is_connected()))
                #     await asyncio.sleep(
                #         0.5
                #     )
                # client.set_disconnected_callback(disconnect_callback)

                services = await client.get_services()
                for s in services:
                    for char in s.characteristics:
                        # print(f'Characteristic: {char}')
                        print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')
                        handle_desc_pairs[char.handle] = (char.description + ':')

                await client.start_notify('15005991-b131-3396-014c-664c9867b917', notification_handler)
                await client.start_notify('6eb675ab-8bd1-1b9a-7444-621e52ec6823', notification_handler)

                while True:
                    await asyncio.sleep(5.0)

        except BleakDotNetTaskError:
            print("Peripheral busy. Trying again.")
            pass
        except BleakError:
            print("Didn't connect in time. Retrying.")
            pass


if __name__ == "__main__":
    global handle_desc_pairs
    handle_desc_pairs = {}

    if not path.exists(os.getcwd() + '/data/streamed_data.csv'):
        os.makedirs(os.getcwd() + '/data', exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Time:', 'Temp Value:', 'Strain Value:'])
        new_file_headers.to_csv('data/streamed_data.csv', encoding='utf-8', index=False)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop))

