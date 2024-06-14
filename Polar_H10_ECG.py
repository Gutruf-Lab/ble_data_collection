import _tkinter

from bleak import BleakClient, discover, BleakScanner
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

target_ble_address = "C5:B6:5F:E3:E1:B5"
target_device_name = "Polar H10"
address_hash = ""
output_file_name = ""

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
last_timestamp_ns = 0
timestamp_ns = 0


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
            # y_lower = min(y_data) - (avg_y-min(y_data))/2
            y_lower = -1
            # y_upper = max(y_data) + (max(y_data)-avg_y)/2
            y_upper = 5
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


# Function to convert 3-byte 14-bit signed integer
def convert_3byte_to_14bit_signed(data):
    # Combine the bytes into a 24-bit unsigned integer
    value = int.from_bytes(data, byteorder='little', signed=False)

    # Extract the 14-bit value
    value &= 0x3FFF

    # Convert to signed 14-bit
    if value & 0x2000:
        value -= 0x4000

    return value


def generate_time_points(total_delay, num_pts):
    # Calculate the sampling interval
    interval = total_delay / num_pts
    # Create an array of 73 evenly spaced time points
    time_points = np.arange(0, total_delay, interval)
    timestamps = [x + (time.time() - start_time) for x in time_points]
    return timestamps


def ecg_notification_handler(sender, data):
    global output_file_name
    global xs
    global ys
    global last_timestamp_ns
    global timestamp_ns
    identifier_1 = data[0]
    last_timestamp_ns = struct.unpack('<Q', data[1:9])[0]
    identifier_2 = data[9]
    ecg_readings = []

    delay = (last_timestamp_ns - timestamp_ns) / 1000 / 1000 / 1000
    if delay > 500000000:
        delay = 560.377

    for i in range(10, len(data), 3):
        ecg_reading = convert_3byte_to_14bit_signed(data[i:i+3]) / 1000    # Value is in microvolts
        ecg_readings.append(ecg_reading)

    timestamps = generate_time_points(delay, len(ecg_readings))
    # print(f"Identifier 1: {identifier_1}")
    print(f"New Timestamp (ns): {last_timestamp_ns}")
    print(f"Delay (s): {delay}")
    # print(f"Identifier 2: {identifier_2}")
    print("Timestamps (s):", timestamps)
    print("ECG Readings (mV):", ecg_readings)

    timestamp_ns = last_timestamp_ns

    xs.extend(timestamps)
    ys.extend(ecg_readings)
    xs = xs[-400:]
    ys = ys[-400:]
    update_plot(xs, ys)

    packaged_data = {"Start time:": '',
                     'Elapsed Time:': timestamps,
                     'ECG Readings:': ecg_readings
                     }

    new_df = pd.DataFrame(packaged_data)
    new_df.to_csv(output_file_name, index=False, header=False, mode='a')


def cmd_pt_handler(sender, data):
    print(data)


async def connect_to_device(target_device_name):
    while True:
        try:
            address = ''
            devs = await BleakScanner.discover(timeout=5)
            for d in devs:
                print(d)
                if d.name and len(d.name) > 0 and target_device_name in d.name:
                    address = d.address
                    print('****')
                    print('Device found.')
                    print(f"Attempting connection to {d.name} ({address})...")
                    print('****')
                    break
                    devs[0] = d
            print('----')

            disconnected_event = asyncio.Event()

            def disconnect_callback(client):
                print("Disconnected callback called!")
                disconnected_event.set()

            async with BleakClient(address, disconnected_callback=disconnect_callback) as client:

                # \x02 \x00 [Start_Measurement ECG}
                # \x00 \x01 \x82 \x00 [setting_type(Sample Rate) array_length=1 \x82\x00=130Hz]
                # \x01 \x01 \x0E \x01 [setting_type(Resolution) array_length=1 \x0E\x00=14bit]
                await client.start_notify('FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8', cmd_pt_handler)
                await client.write_gatt_char('FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8', b'\x02\x00\x00\x01\x82\x00\x01\x01\x0E\x00')
                # ECG/PPG String Data
                await client.start_notify('FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8', ecg_notification_handler)
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
    output_file_name = f'{DATA_FILE_PATH}{target_device_name}_{local_time_string}.csv'
    if not path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Start time:', 'Elapsed Time:', 'ECG Readings:'])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)
        packaged_data = {"Start time:": [time.time()],
                         'Elapsed Time:': '',
                         'ECG Readings:': ''
                         }

        new_df = pd.DataFrame(packaged_data)
        new_df.to_csv(output_file_name, index=False, header=False, mode='a')


if __name__ == "__main__":
    connected_devices = 0

    create_csv_if_not_exist(target_device_name)

    try:
        asyncio.run(connect_to_device(target_device_name))
    except TimeoutError as e:
        print(e)
