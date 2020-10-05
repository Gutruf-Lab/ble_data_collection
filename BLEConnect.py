from time import sleep

from bleak import BleakClient, discover
from bleak.exc import BleakDotNetTaskError, BleakError
import asyncio
import pandas as pd
import os
import sys
from os import path
import datetime
import threading
from datetime import timedelta
from collections import defaultdict
import matplotlib
import warnings
warnings.simplefilter("ignore", UserWarning)
sys.coinit_flags = 2


from parse_data import plt


new_data = defaultdict(lambda: "Not found")
# Time in milliseconds (!)
storage_timing = 0
figure_shown=0
lines = []

def notification_handler(sender, data):
    outgoing_data = pd.DataFrame()
    read_data = pd.DataFrame()
    global new_data

    if len(new_data.keys()) < 2:
        new_data["Time:"] = [datetime.datetime.now()]
    print(sender, int.from_bytes(data, byteorder='little'))
    # if handle_desc_pairs[sender] == "Temp Value:":
    #     if new_data[handle_desc_pairs[sender]] == "Not found":
    #         new_data[handle_desc_pairs[sender]] = [int.from_bytes(data, byteorder='little')]
    # else:
    #     if new_data["Temp Value:"] != "Not found":
    #         new_data[handle_desc_pairs[sender]] = [int.from_bytes(data, byteorder='little')]

    if len(new_data.keys()) > 2:
        if datetime.datetime.now() - timedelta(milliseconds=storage_timing) >= new_data["Time:"][0]:
            new_df = pd.DataFrame(new_data)
            print(new_df)

            new_df.to_csv('data/streamed_data.csv',
                                 index=False,
                                 header=False,
                                 mode='a'  # append data to csv file
                                 )

            fig = plt.gcf()
            ax = fig.gca()
            ax.clear()
            data = pd.read_csv('data/streamed_data.csv')
            data["Time:"] = [datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f") for x in data["Time:"]]

            ax = fig.add_subplot(211)
            ax.plot(data['Time:'], data['Temp Value:'], color='red')
            ax.set(xlabel='Time', ylabel='Temperature (Celsius)',
                   title='Temperature Reading')
            ax.ylim = (0, 1024)
            ax.grid()
            rect = ax.patch
            rect.set_facecolor('gainsboro')

            ax2 = fig.add_subplot(212)
            ax2.plot(data['Time:'], data['Strain Value:'], color='blue')
            ax2.set(xlabel='Time', ylabel='Strain Deformation',
                    title='Strain Gauge Reading')
            ax2.ylim = (0, 1024)
            ax2.grid()
            rect = ax2.patch
            rect.set_facecolor('gainsboro')
            plt.subplots_adjust(hspace=0.8)
            plt.draw()
            plt.show()
            plt.pause(1)


            new_data["Time:"] = [datetime.datetime.now()]
            del new_data["Temp Value:"]
            del new_data["Strain Value:"]


async def run(event_loop):

    while True:
        address = ''
        try:
            while address == '':
                devices = await discover(timeout=1)
                for d in devices:
                    print(d)
                    if d.name == 'GUTRUF LAB v0.01':
                        address = d.address
                        print('Device found.')
                print('----')

            async with BleakClient(address, loop=event_loop) as client:
                x = await client.is_connected()

                disconnected_event = asyncio.Event()

                def disconnect_callback(client, future):
                    print("Disconnected callback called!")
                    loop.call_soon_threadsafe(disconnected_event.set)
                    print("Connection lost. Retrying...")

                client.set_disconnected_callback(disconnect_callback)

                services = await client.get_services()
                for s in services:
                    for char in s.characteristics:
                        print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                        # print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')
                        # handle_desc_pairs[char.handle] = (char.description + ':')

                await client.start_notify('15005991-b131-3396-014c-664c9867b917', notification_handler)
                await client.start_notify('6eb675ab-8bd1-1b9a-7444-621e52ec6823', notification_handler)
                await disconnected_event.wait()
                await client.disconnect()
                print("Connected: {0}".format(await client.is_connected()))
        except BleakError:
            print("Didn't connect in time. Retrying.")
            pass


def create_csv_if_not_exist():
    if not path.exists(os.getcwd() + '/data/streamed_data.csv'):
        os.makedirs(os.getcwd() + '/data', exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Time:', 'Temp Value:', 'Strain Value:'])
        new_file_headers.to_csv('data/streamed_data.csv', encoding='utf-8', index=False)


if __name__ == "__main__":
    global handle_desc_pairs

    handle_desc_pairs = {}

    create_csv_if_not_exist()

    # fig = plt.figure()
    # plt.ion()
    #
    # data = pd.read_csv('data/streamed_data.csv')
    # data["Time:"] = [datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f") for x in data["Time:"]]
    # ax = fig.add_subplot(211)
    # ax.plot(data['Time:'], data['Temp Value:'], color='red')
    # ax.set(xlabel='Time', ylabel='Temperature (Celsius)',
    #        title='Temperature Reading')
    # ax.ylim = (0, 1024)
    # ax.grid()
    # rect = ax.patch
    # rect.set_facecolor('gainsboro')
    #
    # ax2 = fig.add_subplot(212)
    # ax2.plot(data['Time:'], data['Strain Value:'], color='blue')
    # ax2.set(xlabel='Time', ylabel='Strain Deformation',
    #        title='Strain Gauge Reading')
    # ax2.ylim = (0, 1024)
    # ax2.grid()
    # rect = ax2.patch
    # rect.set_facecolor('gainsboro')
    # plt.subplots_adjust(hspace=0.8)
    # plt.show()
    # plt.pause(1)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop))

