import _tkinter
from bleak import BleakClient, discover
from bleak.exc import BleakError
import asyncio
import pandas as pd
import os
import sys
from os import path
import time
import warnings
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoLocator
import numpy as np

import struct
from struct import unpack
warnings.simplefilter("ignore", UserWarning)
sys.coinit_flags = 2

NUMBER_OF_SAMPLES = 20
NUM_VALS_PER_SAMPLE = 8

GRAVITY_EARTH = 9.80665
BMI2_GYR_RANGE_2000 = 0

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")


# target_ble_address = "80:EA:CA:70:13:03"
target_ble_address = "1FFC6F31-984D-5A2F-20FE-6223204ECE65"
address_hash = ""
output_file_name = ""

LIVE_DATA_PLOT_ON = False

if LIVE_DATA_PLOT_ON:
    # Some preconfig and setup for the plotting
    fig, ax = plt.subplots()
    xs = [0]
    ys = [0]
    line, = ax.plot(xs, ys)

    # In order to do high speed plotting we use a technique called blitting where we cache the current frame and only
    # render what has changed since the last frame. Otherwise we have to re-render everything each time we update
    # the graph. I create the canvas without any labels or tickmarks and cache that to use later. Then I
    # restore the tickmarks with the default AutoLocator from matplotlib
    ax.set(yticks=[], xticks=[])
    fig.canvas.draw()
    plt.show(block=False)
    background = fig.canvas.copy_from_bbox(fig.bbox)
    ax.yaxis.set_major_locator(AutoLocator())
    ax.xaxis.set_major_locator(AutoLocator())

    start_time = time.time()
    last_refresh_time = 0


def update_plot(x_data, y_data):
    global ax
    global line
    global fig
    global last_refresh_time
    try:
        # Update line with new data
        line.set_xdata(x_data)
        line.set_ydata(y_data)

        # Update bounds at ~60fps
        if time.time() - last_refresh_time > (1/60):
            avg_y = np.mean(y_data)
            y_lower = min(y_data) - (avg_y-min(y_data))/2
            y_upper = max(y_data) + (max(y_data)-avg_y)/2
            ax.set(xlim=(x_data[0], x_data[-1]), ylim=(y_lower, y_upper))

            # I overwrite the last cached frame by restoring the cached blank frame from the beginning of the script
            # Then draw the updated x and y axes and reset the time since we last refreshed the axes
            fig.canvas.restore_region(background)
            ax.draw_artist(ax.xaxis)
            ax.draw_artist(ax.yaxis)
            last_refresh_time = time.time()

        # Plot background (ax.patch), data line, and cache plot with blit to speed up framerate (~10x faster).
        # Flush pushes all changes out of buffer and updates everything immediately
        ax.draw_artist(ax.patch)
        ax.draw_artist(line)
        fig.canvas.blit(ax.clipbox)
        fig.canvas.flush_events()
    except _tkinter.TclError:
        pass


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


def ecg_data_handler(sender, data):
    global output_file_name
    global xs
    global ys
    x = []
    for i in range(len(data)//4):
        subselect = data[i*4:i*4+4]
        subselect = subselect[::-1]
        x.append(struct.unpack('f', subselect))

    # list_of_shorts = list(unpack('f' * (len(data) // 4), data))
    # packaged_data = {"Time:": [time.time()],
    #                  "ECG Reading (mV)": x, "ECG HEX": data.hex()}
    print("Length: ", len(data), end=' ')
    print("Data: ", data)
    print(x)
    # print(packaged_data)

    # if LIVE_DATA_PLOT_ON:
    #     xs.append(time.time() - start_time)
    #     ys.append(x)
    #     xs = xs[-200:]
    #     ys = ys[-200:]
    #     update_plot(xs, ys)

    # new_df = pd.DataFrame(packaged_data)
    # new_df.to_csv(output_file_name, index=False, header=False, mode='a')


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
                await client.is_connected()
                services = await client.get_services()

                for s in services:
                    for char in s.characteristics:
                        # print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                        print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')
                        # characteristic_names[char.handle] = (char.description + ':')
                # name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                # print('\nConnected to device {} ({})'.format(address, name.decode(encoding="utf-8")))

                # ECG Data
                # await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d9e26', ecg_data_handler)
                await client.start_notify('5a87b4ef-3bfa-76a8-e642-92933c31434e', ecg_data_handler)
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
        new_file_headers = pd.DataFrame(columns=['Time:', 'ECG Reading (mV)', 'ECG HEX'])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


if __name__ == "__main__":
    connected_devices = 0
    # hash_addresses()

    create_csv_if_not_exist(target_ble_address)

    try:
        asyncio.run(connect_to_device(target_ble_address))
    except TimeoutError as e:
        print(e)
