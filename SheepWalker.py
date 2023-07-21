#
#   Python BLE interface for Tucker Stuart's Mesh Project
#   Uses the Bleak library to handle notification subscription and callbacks
#   5/30/2021
#   Kevin Kasper (kasper@email.arizona.edu)
#
import datetime

from bleak import BleakClient, discover
from bleak.exc import BleakError
import asyncio
import pandas as pd
import os
import sys
import time
from struct import unpack

# Necessary apparently for multithreading in python. Feel free to optimize.
sys.coinit_flags = 2

connected_devices = 0
NUMBER_OF_READINGS = 12
output_file_name = ""

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")

if os.name == 'nt':
    # addresses = ["80:EA:CA:70:00:01", "80:EA:CA:70:00:02", "80:EA:CA:70:00:05"]
    addresses = ["80:E1:26:1B:72:91"]
else:
    addresses = ["A892DB8D-3048-B6ED-E3D1-0131A8E0A9AB"]

address_hashes = {}
address_filePaths = {}


def hash_addresses():
    global addresses
    for device_address in addresses:
        address_byte_array = bytearray.fromhex(device_address.replace(":", ""))
        address_byte_array.reverse()

        # Initialize with some random large-ish prime
        hashed_address = 5381

        # This is the djb2 hashing algorithm. We don't need security or cryptographic hashing, just string mapping.
        # See more: http://www.cse.yorku.ca/~oz/hash.html
        for b in address_byte_array:
            hashed_address = ((hashed_address << 5) + hashed_address) + b
            hashed_address &= 0xFFFF

        address_hashes[device_address] = hashed_address


def sheep_not_handler(sender, data):
    global output_file_name
    print(datetime.datetime.now(), end='')
    print(" Sheep: [", sender, "]:", data)
    packaged_data = list(unpack('s' * len(data), data))

    decoded_data = ''.join('%02x' % ord(byte) for byte in packaged_data)
    decoded_data = ','.join([decoded_data[i:i + 4] for i in range(0, len(decoded_data), 4)])
    decoded_data = str(datetime.datetime.now().timestamp()) + "," + decoded_data
    print("Decoded data: ", decoded_data)

    with open(output_file_name, 'a') as f:
        f.write(decoded_data)
        f.write("\n")
        f.close()


async def connect_to_device(event_loop, device_address):
    global connected_devices
    while True:
        try:
            print("Attempting connection to " + device_address + "...")

            devices = await discover(timeout=2)
            for d in devices:

                # if d.name not in ["Unknown", "Microsoft", "Apple, Inc.", "", "LE_WH-1000XM4"]:
                print(d)

            async with BleakClient(device_address, loop=event_loop) as client:
                x = await client.is_connected()
                connected_devices += 1
                print("Connected to " + str(connected_devices) + " devices out of " + str(len(address_hashes)) + ".")

                # name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                # print('\nConnected to device {} ({})'.format(device_address, name.decode(encoding="utf-8")))
                disconnected_event = asyncio.Event()

                def disconnect_callback(client):
                    global connected_devices
                    print("Disconnected callback called!")
                    connected_devices -= 1
                    loop.call_soon_threadsafe(disconnected_event.set)
                    print("Connection lost. Retrying...")

                client.set_disconnected_callback(disconnect_callback)

                services = await client.get_services()
                for s in services:
                    for char in s.characteristics:
                        # print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                        print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')

                # Gait Data
                # await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d9e26', gait_notification_handler)
                await client.start_notify('0000fe44-8e22-4541-9d4c-21edae82ed19', sheep_not_handler)

                await disconnected_event.wait()
                await client.disconnect()

                print("Connected: {0}".format(await client.is_connected()))
        except asyncio.exceptions.TimeoutError:
            print("Didn't connect to " + device_address + " in time.")

        except BleakError as err:
            print(err)
            print('----')


def create_file_if_not_exist(filename_address):
    global output_file_name
    output_file_name = DATA_FILE_PATH + filename_address.replace("-", "_") + ".txt"
    if not os.path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
    else:
        num = 1
        # Dynamically add new file to prevent interacting with old data (with each session)
        while os.path.exists(output_file_name):
            output_file_name = DATA_FILE_PATH + filename_address.replace("-", "_") + "(" + str(num) + ")" + ".txt"
            num += 1

    # Store the file path that we're writing to. The gait_notification_handler has no context for what file.
    address_filePaths[filename_address] = output_file_name


if __name__ == "__main__":
    global handle_desc_pairs
    connected_devices = 0
    # hash_addresses()
    # print(address_hashes)

    for address in addresses:
        create_file_if_not_exist(address)

    try:
        loop = asyncio.get_event_loop()
        tasks = asyncio.gather(*(connect_to_device(loop, address) for address in addresses))
        loop.run_until_complete(tasks)
    except TimeoutError as e:
        print(e)