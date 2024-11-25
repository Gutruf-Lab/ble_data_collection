import ctypes

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
import asyncio
import pandas as pd
import os
import sys
from os import path
import time
import warnings
# import RPi.GPIO as GPIO
import struct
from struct import unpack

warnings.simplefilter("ignore", UserWarning)
sys.coinit_flags = 2

friendly_name = "FrailAI"

stream_data = {}
output_file_name = ''

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/ltsheepwearable/2024_april_dipole/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data/ltsheepwearable/2024_april_dipole/")

if os.name == 'nt':
    target_address = "5E:B4:EF:EA:56:4D"
    target_name = "FrailAI"
else:
    target_address = "D15D28B2-DE8A-2943-D43C-20AA7CB47BCF"  # FrailAI Wearable
    target_name = "FrailAI"


def frailty_gait_notification_handler(sender, data):
    global output_file_name
    print(data)

    (last_sample_time,
     time_step,
     skipped_samples_time_offset,
     snippet_start_time) = unpack('f' * 4, data[0:16])

    gyro_z_raw = unpack('h' * 218, data[16:452])

    (exhaust_predict_healthy,
     exhaust_predict_prefrail,
     exhaust_predict_frail) = unpack('fff', data[452:464])
    (slow_predict_healthy,
     slow_predict_prefrail,
     slow_predict_frail) = unpack('fff', data[464:476])
    (overall_frailty_predict_healthy,
     overall_frailty_predict_prefrail,
     overall_frailty_predict_frail) = unpack('fff', data[476:488]) * 100

    sample_point_times = []
    gyro_z = []
    for index, val in enumerate(gyro_z_raw):
        gyro_z.append((2000 / ((float((1 << 16) / 2.0)) + 0)) * val)
        sample_point_times.append(snippet_start_time + (index * time_step))

    packaged_data = {'Received_timestamp:': time.time(),
                     'Time:': sample_point_times,
                     'Gyro_Z:': gyro_z,
                     'Time_step:': time_step,
                     'Exhaustion_Healthy:': exhaust_predict_healthy * 100,
                     'Exhaustion_Prefrail:': exhaust_predict_prefrail * 100,
                     'Exhaustion_Frail:': exhaust_predict_frail * 100,
                     'Slowness_Healthy:': slow_predict_healthy * 100,
                     'Slowness_Prefrail:': slow_predict_prefrail * 100,
                     'Slowness_Frail:': slow_predict_frail * 100,
                     'Overall_Frailty_Healthy:': overall_frailty_predict_healthy * 100,
                     'Overall_Frailty_Prefrail:': overall_frailty_predict_prefrail * 100,
                     'Overall_Frailty_Frail:': overall_frailty_predict_frail * 100
                     }

    print(packaged_data)

    df = pd.DataFrame.from_dict(packaged_data, orient='index')
    df = df.transpose()

    df.to_csv(output_file_name, index=False, header=False, mode='a')


async def connect_to_device(target_device_name, target_device_address):
    global connected_devices
    found_devices = []
    address = None
    while True:
        try:
            devices = await BleakScanner.discover(timeout=3)
            for d in devices:
                # if d.name not in ['Apple, Inc.', 'EarStudio']:
                # if d.address not in addresses:
                #     addresses.append(d.address)
                if d.name:
                    print(d)
                    if len(d.metadata["uuids"]) > 0:
                        print(f'\t{d.metadata["uuids"]}')
                    if d.name == target_device_name:
                        address = d.address
                        print('****')
                        print('Device found.')
                        print("Attempting connection to " + address + "...")
                        print('****')
            print('---------')

            disconnected_event = asyncio.Event()

            def disconnect_callback(client):
                print("Disconnected callback called!")
                disconnected_event.set()

            if target_device_address is not None:
                async with BleakClient(target_device_address, disconnected_callback=disconnect_callback) as client:
                    while not client.is_connected:
                        continue
                    start_time = time.time()

                    for s in client.services:
                        for char in s.characteristics:
                            # print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                            print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')

                    # Raw NFC Data
                    await client.start_notify('00002a37-0000-1000-8000-00805f9b34fb', frailty_gait_notification_handler)

                    # await client.disconnect()
                    # break
                    await disconnected_event.wait()

        except asyncio.exceptions.TimeoutError as e:
            print(e)
            print("----")
        except BleakError as e:
            print(e)
            print('----')


def create_csv_if_not_exist(filename_address):
    global output_file_name
    local_time_string = time.strftime("%Y_%m_%d__%H_%M_%S", time.localtime())
    output_file_name = f'{DATA_FILE_PATH}{friendly_name}_{local_time_string}.csv'
    if not path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Received_timestamp:',
                                                 'Time:',
                                                 'Gyro_Z:',
                                                 'Time_step:',
                                                 'Exhaustion_Healthy:',
                                                 'Exhaustion_Prefrail:',
                                                 'Exhaustion_Frail:',
                                                 'Slowness_Healthy:',
                                                 'Slowness_Prefrail:',
                                                 'Slowness_Frail:',
                                                 'Overall_Frailty_Healthy:',
                                                 'Overall_Frailty_Prefrail:',
                                                 'Overall_Frailty_Frail:'])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


if __name__ == "__main__":
    global handle_desc_pairs
    connected_devices = 0

    create_csv_if_not_exist(target_address)

    try:
        asyncio.run(connect_to_device(target_device_name=target_name,
                                      target_device_address="D15D28B2-DE8A-2943-D43C-20AA7CB47BCF"))
    except TimeoutError as e:
        print(e)
