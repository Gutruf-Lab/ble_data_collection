from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
import asyncio
import pandas as pd
import os
import sys
from os import path
import time
import warnings

import struct
from struct import unpack
warnings.simplefilter("ignore", UserWarning)
sys.coinit_flags = 2

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")


if os.name == 'nt':
    # addresses = ["80:EA:CA:70:00:07","80:EA:CA:70:00:06", "80:EA:CA:70:00:04"]
    target_ble_address = "80:EA:CA:70:00:11"
else:
    target_ble_address = "E5CEF08A-C3F0-950E-3AB3-D7EE337B73C9"

address_hash = ""
output_file_name = ""


def hash_addresses():
    global address_hash

    address_byte_array = bytearray.fromhex(target_ble_address.replace(":", ""))
    address_byte_array.reverse()
    # Initialize with some random large-ish prime
    hashed_address = 5381

    for b in address_byte_array:
        hashed_address = ((hashed_address << 5) + hashed_address) + b
        hashed_address &= 0xFFFF

    address_hash = hashed_address


def osseoimplant_notification_handler(sender, data):
    global output_file_name

    packaged_data = {"Time:": [time.time()],
                     "Gait data:": str(data)}

    print(packaged_data)
    new_df = pd.DataFrame(packaged_data)
    new_df.to_csv(output_file_name, index=False, header=False, mode='a')


async def connect_to_device(address):
    while True:
        try:
            devs = await BleakScanner.discover(timeout=2)
            for d in devs:
                print(d)
                if d.address == address:
                    print('****')
                    print('Device found.')
                    print("Attempting connection to " + address + "...")
                    print('****')
                    break
                    devs[0] = d
            print('----')

            disconnected_event = asyncio.Event()

            def disconnect_callback(client):
                print("Disconnected callback called!")
                disconnected_event.set()

            async with BleakClient(address_or_ble_device=address, disconnected_callback=disconnect_callback) as client:

                # name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                # print('\nConnected to device {} ({})'.format(address, name.decode(encoding="utf-8")))
                for s in client.services:
                    print(f'[Service] {s}')
                    for char in s.characteristics:
                        if "read" in char.properties:
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                print(f"  [Characteristic] {char} ({','.join(char.properties)}), Value: {value}\n")
                            except Exception as e:
                                print(f"  [Characteristic] {char} ({','.join(char.properties)}), Error: {e}\n")
                        else:
                            print(f"  [Characteristic] {char} ({','.join(char.properties)})")

                        for descriptor in char.descriptors:
                            try:
                                value = await client.read_gatt_descriptor(descriptor.handle)
                                print(f"    [Descriptor] {descriptor}, Value: {value}")
                            except Exception as e:
                                print(f"    [Descriptor] {descriptor}, Error: %{e}")
                                
                        # print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                        print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')
                        # characteristic_names[char.handle] = (char.description + ':')

                # 6-Axis IMU Data
                await asyncio.sleep(5)
                await client.start_notify('0000fe44-8e22-4541-9d4c-21edae82ed19', osseoimplant_notification_handler)
                await disconnected_event.wait()

        except asyncio.exceptions.TimeoutError as TimeErr:
            print(TimeErr)
            print("----")
        except BleakError as BLE_Err:
            print(BLE_Err)
            print('----')


def create_csv_if_not_exist(filename_address):
    global output_file_name
    output_file_name = DATA_FILE_PATH + filename_address.replace(":", "_") + ".csv"
    if not path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Time:', 'Gait data:'])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


if __name__ == "__main__":
    connected_devices = 0

    create_csv_if_not_exist(target_ble_address)

    try:
        asyncio.run(connect_to_device(target_ble_address))
    except TimeoutError as e:
        print(e)
