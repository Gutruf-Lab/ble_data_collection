from bleak import BleakClient
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

adc_data = {}
accel_data = {}
gyro_data = {}
lines = []
DEVICE_NAME = 'GUTRUF LAB v3.BAT_MON'
LED_PIN = 27
GRAVITY_EARTH = 9.80665
BMI2_GYR_RANGE_2000 = 0

# GPIO.setmode(GPIO.BCM)
# GPIO.setup(LED_PIN, GPIO.OUT)
pin_flash_cycle_duration = 0
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data/")
DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "data")
characteristic_names = {
     39: 'Temperature:',
     43: 'Strain:',
     54: 'Gyro_X:',
     58: 'Gyro_Y:',
     62: 'Gyro_Z:',
     66: 'Accel_X:',
     70: 'Accel_Y:',
     74: 'Accel_Z:',
     86: 'Battery:'
}

addresses = ["80:EA:CA:70:00:03", "80:EA:CA:70:00:04"]


def store_data_as_csv():
    global adc_data
    global accel_data
    global gyro_data
    store_data = False
    # Create new dict to populate and convert to data frame
    packaged_data = {"Time:": [time.time()]}

    # Check if the adc data is ready, if so prepend it. Otherwise use empty strings
    if len(adc_data.keys()) > 2:
        packaged_data['Temperature:'] = adc_data.pop('Temperature:')
        packaged_data['Strain:'] = adc_data.pop('Strain:')
        packaged_data['Battery:'] = adc_data.pop('Battery:')
        store_data = True
    else:
        packaged_data['Temperature:'] = ""
        packaged_data['Strain:'] = ""
        packaged_data['Battery:'] = ""

    # Make sure both accelerometer and gyro data dicts are populated
    if (len(accel_data.keys()) > 2) and (len(gyro_data.keys()) > 2):
        store_data = True
        # Insert XYZ accelerometer and gyroscope
        for key in sorted(accel_data.keys()):
            packaged_data[key] = accel_data.pop(key)

        for key in sorted(gyro_data.keys()):
            packaged_data[key] = gyro_data.pop(key)

    else:
        packaged_data['Gyro_X:'] = ""
        packaged_data['Gyro_Y:'] = ""
        packaged_data['Gyro_Z:'] = ""
        packaged_data['Accel_X:'] = ""
        packaged_data['Accel_Y:'] = ""
        packaged_data['Accel_Z:'] = ""

    if store_data:
        print(address)
        # Create dataframe from packaged data disc and write to CSV file
        output_file_name = DATA_FILE_PATH + address.replace(":", "_") + ".csv"
        new_df = pd.DataFrame(packaged_data)
        new_df.to_csv(output_file_name,
                      index=False,
                      header=False,
                      mode='a'  # append data to csv file
                      )


def adc_notification_handler(sender, data, dev_address):
    global adc_data
    global pin_flash_cycle_duration
    char_name = characteristic_names[sender]
    # if char_name == 'Temperature:':
    #     GPIO.output(LED_PIN, 1)
    #     pin_flash_cycle_duration += 1
    print("ADC Callback:", dev_address)
    # print(sender, int.from_bytes(data, byteorder='little'))
    adc_data[char_name] = [int.from_bytes(data, byteorder='little')]
    adc_data[char_name] = [int.from_bytes(data, byteorder='little')]

    # if char_name == 'Temperature:' and pin_flash_cycle_duration >= 5:
    #     GPIO.output(LED_PIN, 0)
    #     pin_flash_cycle_duration = 0

    if len(adc_data.keys()) > 2:
        # print(adc_data)
        store_data_as_csv()


def gyro_notification_handler(sender, data):
    global gyro_data
    # Convert characteristic id number to corresponding characteristic name
    char_name = characteristic_names[sender]
    gyro_data[char_name] = [struct.unpack('f', data)]
    store_data_as_csv()


def accel_notification_handler(sender, data):
    global accel_data
    char_name = characteristic_names[sender]
    accel_data[char_name] = [struct.unpack('f', data)]
    store_data_as_csv()


def raw_imu_notification_handler(sender, data):
    # print("IMU: [", sender, "]:", data)
    global accel_data
    global gyro_data
    list_of_shorts = list(unpack('h' * (len(data) // 2), data))
    # print(list_of_shorts)
    for i in range(0, 3):
        list_of_shorts[i] = (9.80665 * list_of_shorts[i] * 2) / (float((1 << 16) / 2.0))

    for i in range(3, 6):
        list_of_shorts[i] = (2000 / ((float((1 << 16) / 2.0)) + 0)) * list_of_shorts[i]

    # print(list_of_shorts)
    accel_data['Accel_X:'] = list_of_shorts[0]
    accel_data['Accel_Y:'] = list_of_shorts[1]
    accel_data['Accel_Z:'] = list_of_shorts[2]
    gyro_data['Gyro_X:'] = list_of_shorts[3]
    gyro_data['Gyro_Y:'] = list_of_shorts[4]
    gyro_data['Gyro_Z:'] = list_of_shorts[5]
    store_data_as_csv()


def battery_notification_handler(sender, data):
    global adc_data
    print(sender, int.from_bytes(data, byteorder='little'))
    adc_data['Battery:'] = int.from_bytes(data, byteorder='little')
    if len(adc_data.keys()) > 2:
        store_data_as_csv()


async def connect_to_device(event_loop, address):
    while True:
        try:
            print("Attempting connection to " + address + "...")
            async with BleakClient(address, loop=event_loop) as client:
                x = await client.is_connected()

                disconnected_event = asyncio.Event()

                def disconnect_callback(client):
                    print("Disconnected callback called!")
                    loop.call_soon_threadsafe(disconnected_event.set)
                    print("Connection lost. Retrying...")

                client.set_disconnected_callback(disconnect_callback)

                services = await client.get_services()
                for s in services:
                    for char in s.characteristics:
                        # print('Characteristic: {0}'.format(await client.get_all_for_characteristic(char)))
                        print(f'[{char.uuid}] {char.description}:, {char.handle}, {char.properties}')
                        handle_desc_pairs[char.handle] = (char.description + ':')
                # Temp Read
                await client.start_notify('15005991-b131-3396-014c-664c9867b917', adc_notification_handler(dev_address=address))
                # Strain Read
                await client.start_notify('6eb675ab-8bd1-1b9a-7444-621e52ec6823', adc_notification_handler(dev_address=address))
                # Battery Monitoring
                await client.start_notify('1587686a-53dc-25b3-0c4a-f0e10c8dee20', adc_notification_handler(dev_address=address))
                # Raw IMU Data
                await client.start_notify('2c86686a-53dc-25b3-0c4a-f0e10c8d9e26', raw_imu_notification_handler)

                await disconnected_event.wait()
                await client.disconnect()

                print("Connected: {0}".format(await client.is_connected()))

        except BleakError as e:
            print(e)


def create_csv_if_not_exist(address):
    output_file_name = DATA_FILE_PATH + address.replace(":", "_") + ".csv"
    if not path.exists(output_file_name):
        os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
        new_file_headers = pd.DataFrame(columns=['Time:', 'Temperature:', 'Strain:', 'Battery:',
                                                 "Accel_X:", "Accel_Y:", "Accel_Z:", "Gyro_X:", "Gyro_Y:", "Gyro_Z:"])
        new_file_headers.to_csv(output_file_name, encoding='utf-8', index=False)


if __name__ == "__main__":
    global handle_desc_pairs

    handle_desc_pairs = {}
    # GPIO.output(LED_PIN, 0)
    for address in addresses:
        create_csv_if_not_exist(address)

    # error catch`
    loop = asyncio.get_event_loop()

    tasks = asyncio.gather(*(connect_to_device(loop, address) for address in addresses))
    try:
        loop.run_until_complete(tasks)
    except TimeoutError as e:
        print(e)
