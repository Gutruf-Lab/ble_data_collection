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
# import oct2py as oct # run matlab scripts in python
import os
import sys
import time
from struct import unpack

# Necessary apparently for multithreading in python. Feel free to optimize.
sys.coinit_flags = 2

connected_devices = 0
NUMBER_OF_READINGS = 10

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")
DF_GOOD_POSTURE = 200  # based off 20hz collection. 1200, 12 df, 20hz
DATA_FRAMES_TO_MODEL = DF_GOOD_POSTURE
DF_BAD_POSTURE = 200
POSTURE_STATUS = b"\x00"

if os.name == 'nt':
    # addresses = ["80:EA:CA:70:00:07","80:EA:CA:70:00:06", "80:EA:CA:70:00:04"]
    addresses = ["80:EA:CA:70:00:11"]
else:
    addresses = []

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


def gait_notification_handler(sender, data):
    global connected_devices
    global DATA_FRAMES_TO_MODEL
    global DF_GOOD_POSTURE
    global DF_BAD_POSTURE
    global POSTURE_STATUS
    if connected_devices == len(address_hashes):
        #print(data)
        list_of_shorts = list(unpack('h' * (len(data) // 2), data))
        # print(list_of_shorts)
        # Convert int16_t to uint16_t
        list_of_shorts[NUMBER_OF_READINGS *
                       8] = list_of_shorts[NUMBER_OF_READINGS*8] + 2 ** 16
        #print("d ", end='')

        for i in range(0, NUMBER_OF_READINGS):
            # Convert raw bytearray into list of processed shorts and then package for storage
            # bytearray structure is [16-bit Accel Z, 16-bit Gyro Z, 32-bit Timestamp, 16-bit Address Hash]

            # IMU accelerometer and gyroscope processing taken from Bosch BMI270 interfacing library.
            list_of_shorts[0 + i*8] = (9.80665 * list_of_shorts[0 + i*8]
                                       * 2) / (float((1 << 16) / 2.0))
            list_of_shorts[1 + i*8] = (9.80665 * list_of_shorts[1 + i*8]
                                       * 2) / (float((1 << 16) / 2.0))
            list_of_shorts[2 + i*8] = (9.80665 * list_of_shorts[2 + i*8]
                                       * 2) / (float((1 << 16) / 2.0))
            list_of_shorts[3 + i*8] = (2000 / ((float((1 << 16) / 2.0)) + 0)
                                       ) * list_of_shorts[3 + i*8]
            list_of_shorts[4 + i*8] = (2000 / ((float((1 << 16) / 2.0)) + 0)
                                       ) * list_of_shorts[4 + i*8]
            list_of_shorts[5 + i*8] = (2000 / ((float((1 << 16) / 2.0)) + 0)
                                       ) * list_of_shorts[5 + i*8]

            packaged_data = {"Time:": [time.time()],
                             "Temperature:": '',
                             "Strain:": '',
                             "Battery:": '',
                             'Accel_X:': list_of_shorts[0 + i*8],
                             'Accel_Y:': list_of_shorts[1 + i*8],
                             'Accel_Z:': list_of_shorts[2 + i*8],
                             'Gyro_X:': list_of_shorts[3 + i*8],
                             'Gyro_Y:': list_of_shorts[4 + i*8],
                             'Gyro_Z:': list_of_shorts[5 + i*8],
                             'Device Timestamp:': ''}

            device_address = next(
                (dev for dev in address_hashes if address_hashes[dev] == list_of_shorts[NUMBER_OF_READINGS*8]), None)

            list_of_shorts[6 + i*8] = int.from_bytes(
                (data[14 + i * 16:16 + i * 16:] + data[12 + i * 16:14 + i * 16:]), "little")
           # print(list_of_shorts[6 + i*8])
            print("data received")
            packaged_data["Device Timestamp:"] = list_of_shorts[6 + i*8]
            # print(packaged_data)
            # Write processed and packaged data out to file
            output_file_name = address_filePaths[device_address]
            # print(output_file_name)

            new_df = pd.DataFrame(packaged_data)
            new_df.to_csv(output_file_name, index=False,
                          header=False, mode='a')
            if len(open(output_file_name, "r").readlines()) >= DATA_FRAMES_TO_MODEL:
                # TODO feed csv to model
                # TODO get model output
                modelOutput = b"\x01"  # 1 is bad posture
                POSTURE_STATUS = modelOutput
                if modelOutput == b"\x01":
                    DATA_FRAMES_TO_MODEL = DF_BAD_POSTURE
                #   TODO send model information to Da14585
                # TODO make new csv
                elif modelOutput == b"\x00":
                    DATA_FRAMES_TO_MODEL = DF_GOOD_POSTURE
                # print(output_file_name)
                # delete_csv(output_file_name)
                create_csv_if_not_exist(addresses[0])

       # print(list_of_shorts)
    else:
        pass
# def model_response_handler():
#     if len(open(output_file_name, "r").readlines()) >= DATA_FRAMES_TO_MODEL:
#                 # TODO feed csv to model
#                 # TODO get model output
#                 modelOutput = 1  # 1 is bad posture

#                 if modelOutput == 1:
#                     DATA_FRAMES_TO_MODEL = DF_BAD_POSTURE
#                 #   TODO send model information to Da14585
#                 # TODO make new csv
#                 elif modelOutput == 0:
#                     DATA_FRAMES_TO_MODEL = DF_GOOD_POSTURE
#                 #print(output_file_name)
#                 # delete_csv(output_file_name)
#                 create_csv_if_not_exist(addresses[0])
#     else:
#         return 0


async def connect_to_device(event_loop, device_address):
    global connected_devices
    while True:
        try:
            print("Attempting connection to " + device_address + "...")

            devices = await discover()
            for d in devices:

                if d.name not in ["Unknown", "Microsoft", "Apple, Inc.", "", "LE_WH-1000XM4"]:
                    print(d)

            async with BleakClient(device_address, loop=event_loop) as client:
                x = await client.is_connected()
                connected_devices += 1
                print("Connected to " + str(connected_devices) +
                      " devices out of " + str(len(address_hashes)) + ".")

                name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                print('\nConnected to device {} ({})'.format(
                    device_address, name.decode(encoding="utf-8")))
                disconnected_event = asyncio.Event()

                def disconnect_callback(client):
                    global connected_devices
                    print("Disconnected callback called!")
                    connected_devices -= 1
                    loop.call_soon_threadsafe(disconnected_event.set)
                    print("Connection lost. Retrying...")

                client.set_disconnected_callback(disconnect_callback)

                # imu Data
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d9e26', gait_notification_handler)
                # write to the other characteristic
                print("posture status" + str(POSTURE_STATUS))
               # await client.write_gatt_char('2c86686a-53dc-25b3-0c4a-f0e10c8d9e27', POSTURE_STATUS)
                await disconnected_event.wait()
                await client.disconnect()

                print("Connected: {0}".format(await client.is_connected()))
        except asyncio.exceptions.TimeoutError:
            print("Didn't connect to " + device_address + " in time.")

        except BleakError as err:
            print(err)
            print('----')


def create_csv_if_not_exist(filename_address):
    output_file_name = DATA_FILE_PATH + \
        filename_address.replace(":", "_") + "(1)" + ".csv"
    if not os.path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
    else:
        num = 1
        # Dynamically add new file to prevent interacting with old data (with each session)
        # num is collection window
        while os.path.exists(output_file_name):
            output_file_name = DATA_FILE_PATH + \
                filename_address.replace(":", "_") + \
                "(" + str(num) + ")" ".csv"
            num += 1

    # Store the file path that we're writing to. The gait_notification_handler has no context for what file.
    address_filePaths[filename_address] = output_file_name

    new_file_headers = pd.DataFrame(columns=['Time:', 'Temperature:', 'Strain:', 'Battery:',
                                             "Accel_X:", "Accel_Y:", "Accel_Z:", "Gyro_X:",
                                             "Gyro_Y:", "Gyro_Z:", "Device Timestamp:"])
    new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


def delete_csv(filename):
    os.popen('rm ./' + filename)
    print("DELETED: " + filename)


if __name__ == "__main__":
    global handle_desc_pairs
    connected_devices = 0
    hash_addresses()
    print(address_hashes)

    for address in addresses:
        create_csv_if_not_exist(address)

    # print(address_filePaths)

    try:
        loop = asyncio.get_event_loop()
        tasks = asyncio.gather(*(connect_to_device(loop, address)
                               for address in addresses))
        loop.run_until_complete(tasks)
    except TimeoutError as e:
        print(e)
