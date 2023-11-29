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

friendly_name = "K-Bot LT"

stream_data = {}
battery_reading = 0
battery_read = False
output_file_name = ''
LED_PIN = 27

# GPIO.setmode(GPIO.BCM)
# GPIO.setup(LED_PIN, GPIO.OUT)
pin_flash_cycle_duration = 0
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/averytest/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data/averytest")

if os.name == 'nt':
    target_address = "80:EA:CA:70:00:05"
else:
    target_address = "02397A94-8E08-970E-8E45-C02D8F8FE79E"
    # target_address = "C6935114-E190-9B4F-2946-4B54D7B9F32E"
    # dania_device = "536AC7CF-184F-E6E5-5578-73AC1348DFA7"


def nfc_tag_notification_handler(sender, data):
    global battery_reading
    global battery_read
    global output_file_name
    # print(data)
    # list_of_shorts = list(unpack('h' * (len(data) // 2), data))
    # print(list_of_shorts)
    nfc_data_string = ''

    for i in range(0, len(data), 2):
        nfc_data_string += f'{f"0x{data[i]:02x}{data[i + 1]:02x}":^1},'    # Insane nested f strings to group bytearray

    packaged_data = {"Received Timestamp:": time.time(),
                     "Battery (mV):": battery_reading if battery_read is False else '',
                     "Streamed Data:": nfc_data_string
                     }
    battery_read = True

    print(packaged_data)

    # df = pd.DataFrame.from_dict(packaged_data, orient='index')
    # df = df.transpose()
    # df_nfc_data = pd.DataFrame(df["Streamed Data:"].str.split(',', expand=True).values)
    # df.drop(columns=['Streamed Data:'])
    # df = pd.merge(df_nfc_data)
    df = pd.DataFrame.from_dict(packaged_data, orient='index')
    df = df.transpose()
    df_nfc_data = pd.DataFrame(df["Streamed Data:"].str.split(',', expand=True).values)
    df = df.drop(columns=['Streamed Data:'])
    df = pd.concat([df, df_nfc_data], ignore_index=True, join='inner', axis=1)

    df.to_csv(output_file_name, index=False, header=False, mode='a')


async def connect_to_device(address):
    global connected_devices
    global battery_reading
    while True:
        try:
            devices = await BleakScanner.discover(timeout=2)
            for d in devices:
                print(d)
                if d.address == address:
                    print('****')
                    print('Device found.')
                    print("Attempting connection to " + address + "...")
                    print('****')
            # print('----')

            disconnected_event = asyncio.Event()

            def disconnect_callback(client):
                print("Disconnected callback called!")
                disconnected_event.set()

            async with BleakClient(address, disconnected_callback=disconnect_callback) as client:
                while not client.is_connected:
                    continue
                start_time = time.time()
                # name = await client.read_gatt_char("2A24")
                # print(f'\nConnected to device {address} ({name.decode(encoding="utf-8")})')

                for s in client.services:
                    for char in s.characteristics:
                        # print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                        print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')
                        # characteristic_names[char.handle] = (char.description + ':')
                # name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                # print('\nConnected to device {} ({})'.format(address, name.decode(encoding="utf-8")))

                # Read Battery Level
                battery_reading = await client.read_gatt_char('0000fe43-8e22-4541-9d4c-21edae82ed19')
                battery_reading = unpack('h' * (len(battery_reading) // 2), battery_reading)[0]
                print(f"Battery level: {battery_reading}")
                # Raw NFC Data
                await client.start_notify('0000fe44-8e22-4541-9d4c-21edae82ed19', nfc_tag_notification_handler)
                await asyncio.sleep(20)
                await client.disconnect()
                if not battery_read:
                    df = pd.DataFrame.from_dict({"Received Timestamp:": start_time,
                                                 "Battery (mV):": battery_reading,
                                                 "Streamed Data:": '',
                                                 }, orient='index')
                    df = df.transpose()
                    df.to_csv(output_file_name, index=False, header=False, mode='a')

                df = pd.DataFrame.from_dict({"Received Timestamp:": time.time(),
                                             "Battery (mV):": '',
                                             "Streamed Data:": '',
                                             }, orient='index')
                df = df.transpose()
                df.to_csv(output_file_name, index=False, header=False, mode='a')
                break
                # await disconnected_event.wait()

        except asyncio.exceptions.TimeoutError as e:
            print(e)
            print("----")
        except BleakError as e:
            print(e)
            print('----')


def create_csv_if_not_exist(filename_address):
    global output_file_name
    local_time_string = time.strftime("%Y_%m_%d__%H_%M_%S", time.localtime())
    output_file_name = f'{DATA_FILE_PATH}{friendly_name}_leg_{local_time_string}.csv'
    if not path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Received timestamp:',  'Battery (mV):', 'Streamed Data:'])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


if __name__ == "__main__":
    global handle_desc_pairs
    connected_devices = 0

    # GPIO.output(LED_PIN, 0)
    create_csv_if_not_exist(target_address)

    try:
        asyncio.run(connect_to_device(address=target_address))
    except TimeoutError as e:
        print(e)
