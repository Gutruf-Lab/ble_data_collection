'''
  Python BLE interface for Tucker Stuart's Mesh Project
  Uses the Bleak library to handle notification subscription and callbacks
  5/30/2021
  Kevin Kasper (kasper@arizona.edu), Brandon Good (brandongood@arizona.edu)
'''
from shutil import ReadError
from statistics import mean
import joblib

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
NUMBER_OF_READINGS = 10

# storage for wearable data
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")

'''toggles for changing # of data frames to send to model
        ex. if wearable currently thinks the posture is bad,
            this script will change the number of data frames 
            required to run the model to DF_BAD_POSTURE
            to effectively lower the amount of time before the
            next posture evaluation
'''
DF_GOOD_POSTURE = 200  # based off 20hz collection. 1200, 12 df, 20hz
DATA_FRAMES_TO_MODEL = 200
DF_BAD_POSTURE = 200

# model output of posture status
POSTURE_STATUS = b"\x00"
# flag for if model is called, result gathered, and now its time to
# send response to the wearable
WRITE_TO_CLIENT = False

# motor parameters - will set both motors to these settings
HM_DUTY_CYCLE = b"\x54"  # 84 in decimal
HM_T1 = b"\x0A"  # in multiples of 10ms
HM_T2 = b"\x14"

# aggregator for our average readings
READINGS = {
    # "Time:": [time.time()],
    #  "Temperature:": '',
    #  "Strain:": '',
    #  "Battery:": '',
    'Accel_X:': [],
    'Accel_Y:': [],
    'Accel_Z:': [],
    'Gyro_X:': [],
    'Gyro_Y:': [],
    'Gyro_Z:': []
    # 'Device Timestamp:': ''
}

if os.name == 'nt':
    # addresses = ["80:EA:CA:70:00:07","80:EA:CA:70:00:06", "80:EA:CA:70:00:04"]
    addresses = ["80:EA:CA:70:00:11"]
else:  # else, we're on MacOS
    # this will be different on every Mac computer.
    addresses = ["6DFB2C3D-3B33-F0EC-127F-B7B1AE23FFFC"]
    # TODO reconfigure for something more generic

address_hashes = {}
address_filePaths = {}
output_file_name = ''


def hash_addresses():
    global addresses
    for device_address in addresses:
        address_byte_array = bytearray.fromhex(
            device_address.replace(":", "").replace("-", "_"))
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
    global WRITE_TO_CLIENT
    global READINGS
    # global output_file_name
    if connected_devices == len(address_hashes) or os.name != 'nt':
        # print(data)
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

            packaged_data = {
                # "Time:": [time.time()],
                #  "Temperature:": '',
                #  "Strain:": '',
                #  "Battery:": '',
                'Accel_X:': list_of_shorts[0 + i*8],
                'Accel_Y:': list_of_shorts[1 + i*8],
                'Accel_Z:': list_of_shorts[2 + i*8],
                'Gyro_X:': list_of_shorts[3 + i*8],
                'Gyro_Y:': list_of_shorts[4 + i*8],
                'Gyro_Z:': list_of_shorts[5 + i*8]
                # 'Device Timestamp:': ''
            }
            READINGS['Accel_X:'].append(list_of_shorts[0 + i*8])
            READINGS['Accel_Y:'].append(list_of_shorts[1 + i*8])
            READINGS['Accel_Z:'].append(list_of_shorts[2 + i*8])
            READINGS['Gyro_X:'].append(list_of_shorts[3 + i*8])
            READINGS['Gyro_Y:'].append(list_of_shorts[4 + i*8])
            READINGS['Gyro_Z:'].append(list_of_shorts[5 + i*8])
            device_address = next(
                (dev for dev in address_hashes if address_hashes[dev] == list_of_shorts[NUMBER_OF_READINGS*8]), None)

            list_of_shorts[6 + i*8] = int.from_bytes(
                (data[14 + i * 16:16 + i * 16:] + data[12 + i * 16:14 + i * 16:]), "little")
            # print(list_of_shorts[6 + i*8])
            # packaged_data["Device Timestamp:"] = list_of_shorts[6 + i*8]
            # print(packaged_data)
            # Write processed and packaged data out to file
            output_file_name = address_filePaths[device_address]
            # print(output_file_name)

            new_df = pd.DataFrame(packaged_data, index=[0])
            new_df.to_csv(output_file_name, index=False,
                          header=False, mode='a')
            if len(READINGS['Accel_X:']) >= DATA_FRAMES_TO_MODEL:

                averages = {
                    # "Time:": [time.time()],
                    #  "Temperature:": '',
                    #  "Strain:": '',
                    #  "Battery:": '',
                    'Accel_X:': [mean(READINGS['Accel_X:'])],
                    'Accel_Y:': [mean(READINGS['Accel_Y:'])],
                    'Accel_Z:': [mean(READINGS['Accel_Z:'])],
                    'Gyro_X:': [mean(READINGS['Gyro_X:'])],
                    'Gyro_Y:': [mean(READINGS['Gyro_Y:'])],
                    'Gyro_Z:': [mean(READINGS['Gyro_Z:'])]
                    # 'Device Timestamp:': ''
                }
                print(averages)
                avgdf = pd.DataFrame(data=averages)
                loaded_model = joblib.load('Completed_model.joblib')
                model_result = loaded_model.predict(avgdf)
                print('RESULT: ', model_result)
                if model_result == [1]:
                    POSTURE_STATUS = b"\x01"
                    DATA_FRAMES_TO_MODEL = DF_GOOD_POSTURE
                elif model_result == [0]:
                    POSTURE_STATUS = b"\x00"
                    DATA_FRAMES_TO_MODEL = DF_BAD_POSTURE
                # print(output_file_name)
                # delete_csv(output_file_name)
                WRITE_TO_CLIENT = True
                # empty readings
                READINGS = {
                    # "Time:": [time.time()],
                    #  "Temperature:": '',
                    #  "Strain:": '',
                    #  "Battery:": '',
                    'Accel_X:': [],
                    'Accel_Y:': [],
                    'Accel_Z:': [],
                    'Gyro_X:': [],
                    'Gyro_Y:': [],
                    'Gyro_Z:': []
                    # 'Device Timestamp:': ''
                }
                averages = {}

                create_csv_if_not_exist(addresses[0])

        # print(list_of_shorts)
        print("data received")
    else:
        pass


async def set_motor_defaults(client):
    global HM_DUTY_CYCLE
    global HM_T1
    global HM_T2
    # hm1 duty cycle
    await client.write_gatt_char('2D86686A-53DC-25B3-0C4A-F0E10C8DEE20', HM_DUTY_CYCLE)
    # hm2 duty cycle
    await client.write_gatt_char('5A87B4EF-3BFA-76A8-E642-92933C31434F', HM_DUTY_CYCLE)
    # hm1 t1
    await client.write_gatt_char('2D86686A-53DC-25B3-0C4A-F0E10C8DEE2A', HM_T1)
    # hm2 t1
    await client.write_gatt_char('5A87B4EF-3BFA-76A8-E642-92933C314350', HM_T1)
    # hm1 t2
    await client.write_gatt_char('2D86686A-53DC-25B3-0C4A-F0E10C8DEE22', HM_T2)
    # hm2 t2
    await client.write_gatt_char('5A87B4EF-3BFA-76A8-E642-92933C314351', HM_T2)


async def connect_to_device(event_loop, device_address):
    global connected_devices
    global WRITE_TO_CLIENT
    while True:
        try:
            print("Attempting connection to " + device_address + "...")

            devices = await discover()
            for d in devices:

                if d.name not in ["Unknown", "Microsoft", "Apple, Inc.", "", "LE_WH-1000XM4"]:
                    print(d)

            async with BleakClient(device_address, loop=event_loop) as client:
                while not client.is_connected:
                    pass
                connected_devices += 1
                print("Connected to " + str(connected_devices) +
                      " devices out of " + str(len(address_hashes)) + ".")

                # name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                # print('\nConnected to device {} ({})'.format(
                #     device_address, name.decode(encoding="utf-8")))

                services = await client.get_services()

                for service in services:
                    print('\nservice', service.handle,
                          service.uuid, service.description)

                    characteristics = service.characteristics

                    for char in characteristics:
                        print('  characteristic', char.handle, char.uuid,
                              char.description, char.properties)

                        descriptors = char.descriptors

                        for desc in descriptors:
                            print('    descriptor', desc)

                disconnected_event = asyncio.Event()

                def disconnect_callback(client):
                    global connected_devices
                    print("Disconnected callback called!")
                    connected_devices -= 1
                    loop.call_soon_threadsafe(disconnected_event.set)
                    print("Connection lost. Retrying...")

                client.set_disconnected_callback(disconnect_callback)
                # await set_motor_defaults(client)
                # imu Data
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d9e26', gait_notification_handler)
                # write to the other characteristic
                while client.is_connected:
                    if WRITE_TO_CLIENT:
                        await client.write_gatt_char('2c86686a-53dc-25b3-0c4a-f0e10c8d9e27', POSTURE_STATUS)
                        print("posture status sent  " + str(POSTURE_STATUS))
                        await asyncio.sleep(1.0)
                        WRITE_TO_CLIENT = False
                    await asyncio.sleep(1.0)
                await disconnected_event.wait()
                await client.disconnect()
                while 1:
                    pass
                # print("Connected: {0}".format(await client.is_connected()))
        except asyncio.exceptions.TimeoutError:
            print("Didn't connect to " + device_address + " in time.")

        except BleakError as err:
            print(err)
            print('----')


def create_csv_if_not_exist(filename_address):
    global output_file_name
    output_file_name = DATA_FILE_PATH + \
        filename_address.replace(":", "_").replace("-", "_") + "(1)" + ".csv"
    if not os.path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
    else:
        num = 1
        # Dynamically add new file to prevent interacting with old data (with each session)
        # num is collection window
        while os.path.exists(output_file_name):
            output_file_name = DATA_FILE_PATH + \
                filename_address.replace(":", "_").replace("-", "_") + \
                "(" + str(num) + ")" ".csv"
            num += 1

    # Store the file path that we're writing to. The gait_notification_handler has no context for what file.
    address_filePaths[filename_address] = output_file_name

    # if you want file headers...
    new_file_headers = pd.DataFrame(columns=[
        #  'Time:',
        #  'Temperature:',
        #  'Strain:',
        #  'Battery:',
        "Accel_X:", "Accel_Y:", "Accel_Z:",
        "Gyro_X:", "Gyro_Y:", "Gyro_Z:",
        #  "Device Timestamp:"
    ])
    new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


def delete_csv(filename):
    os.popen('rm ./' + filename)
    print("DELETED: " + filename)


if __name__ == "__main__":
    global handle_desc_pairs
    connected_devices = 0
    if os.name == 'nt':
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
