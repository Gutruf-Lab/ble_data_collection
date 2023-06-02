from bleak import BleakClient, discover
from bleak.exc import BleakError
import asyncio
import pandas as pd
import os
import sys
from os import path
import time
import warnings
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
# import matplotlib
# matplotlib.use("TkAgg")

import struct
from struct import unpack
warnings.simplefilter("ignore", UserWarning)
sys.coinit_flags = 2

NUMBER_OF_SAMPLES = 12
NUM_VALS_PER_SAMPLE = 8

GRAVITY_EARTH = 9.80665
BMI2_GYR_RANGE_2000 = 0

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")

target_ble_address = "80:EA:CA:70:00:11"
address_hash = ""
output_file_name = ""

fig, ax = plt.subplots()
ax.set(ylim=[-10, 10])
xs = [0]
ys = [0]
line, = ax.plot(xs, ys)
fig.canvas.draw()
plt.show(block=False)


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


def six_axis_notification_handler(sender, data):
    global output_file_name
    global xs
    global ys
    global ax
    global line
    global fig
    list_of_shorts = list(unpack('h' * (len(data) // 2), data))
    print(list_of_shorts)
    list_of_shorts[NUMBER_OF_SAMPLES] = list_of_shorts[NUMBER_OF_SAMPLES] + 2 ** 16

    for i in range(0, NUMBER_OF_SAMPLES):
        # Convert raw bytearray into list of processed shorts and then package it for storage
        # bytearray structure is [Accel X, Accel Y, Accel Z, Gyro X, Gyro Y, Gyro Z, Timestamp, Address Hash]
        offset = i*NUM_VALS_PER_SAMPLE
        list_of_shorts[0 + offset] = (GRAVITY_EARTH * list_of_shorts[0 + offset] * 2) / (float((1 << 16) / 2.0))
        list_of_shorts[1 + offset] = (GRAVITY_EARTH * list_of_shorts[1 + offset] * 2) / (float((1 << 16) / 2.0))
        list_of_shorts[2 + offset] = (GRAVITY_EARTH * list_of_shorts[2 + offset] * 2) / (float((1 << 16) / 2.0))
        list_of_shorts[3 + offset] = (2000 / ((float((1 << 16) / 2.0)) + BMI2_GYR_RANGE_2000)) * list_of_shorts[3 + offset]
        list_of_shorts[4 + offset] = (2000 / ((float((1 << 16) / 2.0)) + BMI2_GYR_RANGE_2000)) * list_of_shorts[4 + offset]
        list_of_shorts[5 + offset] = (2000 / ((float((1 << 16) / 2.0)) + BMI2_GYR_RANGE_2000)) * list_of_shorts[5 + offset]

        # Timestamp values are bytes 11 & 12 + 13 & 14
        # Convert int16_t to uint16_t
        list_of_shorts[6 + offset] = int.from_bytes(
            (data[14 + offset:16 + offset:] + data[12 + offset:14 + offset:]), "little")

        packaged_data = {"Time:": [time.time()],
                         "Temperature:": '',
                         "Strain:": '',
                         "Battery:": '',
                         'Accel_X:': list_of_shorts[0 + offset],
                         'Accel_Y:': list_of_shorts[1 + offset],
                         'Accel_Z:': list_of_shorts[2 + offset],
                         'Gyro_X:': list_of_shorts[3 + offset],
                         'Gyro_Y:': list_of_shorts[4 + offset],
                         'Gyro_Z:': list_of_shorts[5 + offset],
                         'Device Timestamp:': list_of_shorts[6 + offset]}

        print(packaged_data)


        # Add x and y to lists
        xs.append(time.time())
        ys.append(list_of_shorts[0 + offset])
        xs = xs[-100:]
        ys = ys[-100:]

        # print('Xs: ', end='')
        # print(xs)
        # print('Ys: ', end='')
        # print
        ax.set(xlim=(xs[0], xs[-1]))
        line.set_xdata(xs)
        line.set_ydata(ys)
        ax.draw_artist(ax.patch)
        ax.draw_artist(line)
        fig.canvas.blit(ax.bbox)
        fig.canvas.flush_events()

        # plt.gcf().canvas.draw_idle()
        # plt.plot(xs, ys)
        # plt.pause(0.000001)
        # plt.clf()

        new_df = pd.DataFrame(packaged_data)
        new_df.to_csv(output_file_name, index=False, header=False, mode='a')


async def connect_to_device(address):
    while True:
        try:
            devs = await discover(timeout=2)
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

            async with BleakClient(address, disconnected_callback=disconnect_callback) as client:

                name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                print('\nConnected to device {} ({})'.format(address, name.decode(encoding="utf-8")))

                # 6-Axis IMU Data
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d9e26', six_axis_notification_handler)
                await disconnected_event.wait()

        except asyncio.exceptions.TimeoutError as TimeErr:
            print(TimeErr)
            print("----")
        except BleakError as BLE_Err:
            print(BLE_Err)
            print('----')
        except AttributeError as Att_Err:
            print(Att_Err)
            print('----')

def create_csv_if_not_exist(filename_address):
    global output_file_name
    output_file_name = DATA_FILE_PATH + filename_address.replace(":", "_") + ".csv"
    if not path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Time:', 'Temperature:', 'Strain:', 'Battery:',
                                                 "Accel_X:", "Accel_Y:", "Accel_Z:", "Gyro_X:",
                                                 "Gyro_Y:", "Gyro_Z:", "Device Timestamp:"])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


if __name__ == "__main__":
    connected_devices = 0
    hash_addresses()

    create_csv_if_not_exist(target_ble_address)

    # ani = animation.FuncAnimation(fig=fig, func=update, frames=40, interval=30)

    try:
        asyncio.run(connect_to_device(target_ble_address))
    except TimeoutError as e:
        print(e)


