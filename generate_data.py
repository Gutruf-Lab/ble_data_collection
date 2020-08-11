#!/usr/bin/env python
import datetime
import csv
import random
import os


def generate_data():
    start_time = datetime.datetime.now()
    time_delta = datetime.timedelta(milliseconds=-1)
    generated_values = []
    columns = ['Time:', 'Reading:']
    generated_values.append(columns)

    for i in range(0,100):
        entry = (start_time.timestamp(), random.randint(0, 100))
        generated_values.append(entry)
        start_time = start_time + time_delta

    return generated_values


def store_data(data):
    os.makedirs(os.getcwd()+'/data', exist_ok=True)
    with open('data/generated_data.csv', 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',')
        for row in data:
            writer.writerow(row)


if __name__ == "__main__":
    store_data(generate_data())
    print("Data generated.")



