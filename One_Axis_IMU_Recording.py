#
#   Python BLE interface for Tucker Stuart's Mesh Project
#   Uses the Bleak library to handle notification subscription and callbacks
#   5/30/2021
#   Kevin Kasper (kasper@email.arizona.edu)
#

from bleak import BleakClient, discover
from bleak.exc import BleakError
import asyncio
import pandas as pd
import os
import sys
import time
from struct import unpack
from os import path

# Necessary apparently for multithreading in python. Feel free to optimize.
sys.coinit_flags = 2

connected_devices = 0
NUMBER_OF_READINGS = 12


friendly_name = "Dania RD"
target_name = "Dania RD"
output_file_name = ''

pin_flash_cycle_duration = 0
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/flinn_2/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data/flinn_2/")


if os.name == 'nt':
    # addresses = ["80:EA:CA:70:00:01", "80:EA:CA:70:00:02", "80:EA:CA:70:00:05"]
    addresses = ["80:EA:CA:70:00:05"]
else:
    target_address = "0362563D-F2AB-7ECD-0EB0-FD65F64433B4"

address_hashes = {}
address_filePaths = {}


# def hash_addresses():
#     global addresses
#     for device_address in addresses:
#         address_byte_array = bytearray.fromhex(device_address.replace(":", ""))
#         address_byte_array.reverse()
#
#         # Initialize with some random large-ish prime
#         hashed_address = 5381
#
#         # This is the djb2 hashing algorithm. We don't need security or cryptographic hashing, just string mapping.
#         # See more: http://www.cse.yorku.ca/~oz/hash.html
#         for b in address_byte_array:
#             hashed_address = ((hashed_address << 5) + hashed_address) + b
#             hashed_address &= 0xFFFF
#
#         address_hashes[device_address] = hashed_address


def gait_notification_handler(sender, data):
    global connected_devices
    global output_file_name

    if connected_devices == len(address_hashes):
        list_of_shorts = list(unpack('h' * (len(data) // 2), data))
        # print(data)
        # Convert int16_t to uint16_t
        if list_of_shorts[NUMBER_OF_READINGS*4] < 0:
            list_of_shorts[NUMBER_OF_READINGS*4] = list_of_shorts[NUMBER_OF_READINGS*4] + 2 ** 16
        # print("d ", end='')
        for i in range(0, NUMBER_OF_READINGS):
            # Convert raw bytearray into list of processed shorts and then package for storage
            # bytearray structure is [16-bit Accel Z, 16-bit Gyro Z, 32-bit Timestamp, 16-bit Address Hash]

            # IMU accelerometer and gyroscope processing taken from Bosch BMI270 interfacing library.
            list_of_shorts[0 + i*4] = (9.80665 * list_of_shorts[0 + i*4] * 2) / (float((1 << 16) / 2.0))
            list_of_shorts[1 + i*4] = (2000 / ((float((1 << 16) / 2.0)) + 0)) * list_of_shorts[1 + i*4]

            packaged_data = {"Time:": [time.time()],
                             "Temperature:": '',
                             "Strain:": '',
                             "Battery:": '',
                             'Accel_X:': '',
                             'Accel_Y:': list_of_shorts[0 + i*4],
                             'Accel_Z:': '',
                             'Gyro_X:': list_of_shorts[1 + i*4],
                             'Gyro_Y:': '',
                             'Gyro_Z:': '',
                             'Device Timestamp:': ''}

            device_address = next((dev for dev in address_hashes if address_hashes[dev] == list_of_shorts[NUMBER_OF_READINGS*4]), None)

            list_of_shorts[2 + i*4] = int.from_bytes((data[6 + i * 8:8 + i * 8:] + data[4 + i * 8:6 + i * 8:]), "little")
            packaged_data["Device Timestamp:"] = list_of_shorts[2 + i*4]
            # print("List of Shorts:", list_of_shorts)
            print("Packaged Data:", packaged_data)

            # Write processed and packaged data out to file
            # output_file_name = address_filePaths[device_address]
            # print(output_file_name)
            # print(packaged_data)
            new_df = pd.DataFrame(packaged_data)
            new_df.to_csv(output_file_name, index=False, header=False, mode='a')
        # print(list_of_shorts)
    else:
        pass


async def connect_to_device(device_address):
    global connected_devices
    address = None
    while True:
        try:
            # print("Attempting connection to " + device_address + "...")

            devices = await discover(timeout=2)
            for d in devices:

                if d.name not in ["Unknown", "Microsoft", "Apple, Inc.", "", "LE_WH-1000XM4"]:
                    print(d)

            disconnected_event = asyncio.Event()

            def disconnect_callback(client):
                print("Disconnected callback called!")
                disconnected_event.set()

            async with BleakClient(device_address, disconnected_callback=disconnect_callback) as client:

                # Gait Data
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d9e26', gait_notification_handler)

                await disconnected_event.wait()
                await client.disconnect()

                print("Connected: {0}".format(await client.is_connected()))
        except asyncio.exceptions.TimeoutError:
            print("Didn't connect to " + device_address + " in time.")

        except BleakError as err:
            print(err)
            print('----')


def create_csv_if_not_exist(filename_address):
    global output_file_name
    local_time_string = time.strftime("%Y_%m_%d__%H_%M_%S", time.localtime())
    output_file_name = f'{DATA_FILE_PATH}{friendly_name}_{local_time_string}.csv'
    if not path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)

        new_file_headers = pd.DataFrame(columns=['Time:', 'Temperature:', 'Strain:', 'Battery:',
                                                 "Accel_X:", "Accel_Y:", "Accel_Z:", "Gyro_X:",
                                                 "Gyro_Y:", "Gyro_Z:", "Device Timestamp:"])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


if __name__ == "__main__":
    global handle_desc_pairs
    connected_devices = 0
    # hash_addresses()
    # print(address_hashes)

    create_csv_if_not_exist(target_address)

    try:
        asyncio.run(connect_to_device(target_address))
    except TimeoutError as e:
        print(e)
