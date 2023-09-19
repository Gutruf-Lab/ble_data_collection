import _tkinter

from bleak import BleakClient, discover
from bleak.exc import BleakError
import asyncio
import pandas as pd
import numpy as np
import os
import sys
from os import path
import time
import warnings
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoLocator
import struct
warnings.simplefilter("ignore", UserWarning)
sys.coinit_flags = 2

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")

target_ble_address = "40:E0:CA:70:00:01"
output_file_name = ""
friendly_name = "CWH1"

# Some preconfig and setup for the plotting
# fig, ax = plt.subplots(figsize=(12, 10))
fig, ax = plt.subplots()
xs = [0]
ys = [0]
line, = ax.plot(xs, ys)

# In order to do high speed plotting we use a technique called blitting where we cache the frame and only render what
# has changed since the last frame. Otherwise we have to re-render everything each time we update the graph.
# I create the canvas without any tickmarks and cache that to use later. Then I
# restore the tickmarks with the default AutoLocator from matplotlib
ax.set(yticks=[], xticks=[])
fig.canvas.draw()
plt.show(block=False)
background = fig.canvas.copy_from_bbox(fig.bbox)
ax.yaxis.set_major_locator(AutoLocator())
ax.xaxis.set_major_locator(AutoLocator())

start_time = time.time()
last_refresh_time = 0
last_humid_therm_read_time = time.time();


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


def ppg_notification_handler(sender, data):
    global output_file_name
    global xs
    global ys
    print(data)
    x = struct.unpack('<III'.format(len(data)), data)
    # data_str = x.decode('utf-8')
    red_led = x[0]
    ir_led = x[1]
    green_led = x[2]

    xs.append(time.time()-start_time)
    ys.append(red_led)
    xs = xs[-100:]
    ys = ys[-100:]
    update_plot(xs, ys)

    packaged_data = {"Time:": [time.time()],
                     "Red LED:": red_led,
                     "IR LED:": ir_led,
                     "Green LED:": green_led,
                     "Thermal conductivity:": '',
                     "Humidity:": ''
                     }
    print(packaged_data)

    new_df = pd.DataFrame(packaged_data)
    new_df.to_csv(output_file_name, index=False, header=False, mode='a')


def humid_notification_handler(sender, data):
    global output_file_name
    print(data)
    humid_reading = struct.unpack('<h'.format(len(data)), data)[0]

    packaged_data = {"Time:": [time.time()],
                     "Red LED:": '',
                     "IR LED:": '',
                     "Green LED:": '',
                     "Thermal conductivity:": '',
                     "Humidity:": humid_reading
                     }
    print(packaged_data)

    new_df = pd.DataFrame(packaged_data)
    new_df.to_csv(output_file_name, index=False, header=False, mode='a')


def therm_notification_handler(sender, data):
    global output_file_name
    print(data)
    therm_reading = struct.unpack('<h'.format(len(data)), data)[0]

    packaged_data = {"Time:": [time.time()],
                     "Red LED:": '',
                     "IR LED:": '',
                     "Green LED:": '',
                     "Thermal conductivity:": therm_reading,
                     "Humidity:": ''
                     }
    print(packaged_data)

    new_df = pd.DataFrame(packaged_data)
    new_df.to_csv(output_file_name, index=False, header=False, mode='a')


async def connect_to_device(address):
    global last_humid_therm_read_time
    global output_file_name
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
                while not client.is_connected:
                    continue

                # name = await client.read_gatt_char("2A24")
                # print(f'\nConnected to device {address} ({name.decode(encoding="utf-8")})')

                for s in client.services:
                    for char in s.characteristics:
                        # print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                        print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')

                # name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                # print('\nConnected to device {} ({})'.format(address, name.decode(encoding="utf-8")))
                # {0x21, 0xEE, 0x8D, 0x0C, 0xE1, 0xF0, 0x4A, 0x0C, 0xB3, 0x25, 0xDC, 0x53, 0x6A, 0x68, 0x86, 0x2B}
                # ECG/PPG String Data
                await client.start_notify('2b86686a-53dc-25b3-0c4a-f0e10c8dee25', ppg_notification_handler)
                await client.start_notify('2d86686a-53dc-25b3-0c4a-f0e10c8dee12', therm_notification_handler)
                await client.start_notify('2d86686a-53dc-25b3-0c4a-f0e10c8dee22', humid_notification_handler)

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
    local_time_string = time.strftime("%Y_%m_%d__%H_%M_%S", time.localtime())
    output_file_name = f'{DATA_FILE_PATH}{friendly_name}_{local_time_string}.csv'
    if not path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Time:', "Red LED:", "IR LED:", "Green LED:",
                                                 "Thermal conductivity:", "Humidity:"])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


if __name__ == "__main__":
    connected_devices = 0

    create_csv_if_not_exist(target_ble_address)

    try:
        asyncio.run(connect_to_device(target_ble_address))
    except TimeoutError as e:
        print(e)
