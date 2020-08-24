#!/usr/bin/env python
import csv
import numpy as np # we will use this later, so import it now
import pandas as pd
import datetime
import time
from datetime import date
from bokeh.models import ColumnDataSource
from bokeh.models.tools import HoverTool
from bokeh.palettes import Spectral11
# from bokeh.plotting import figure, output_file, show
from bleak import BleakClient
import matplotlib.pyplot as plt
import numpy as np


def read_data():
    # csv file to be read in
    in_csv = 'data/generated_data.csv'

    # csv to write data to
    out_csv = 'path/to/write/file.csv'

    # get the number of lines of the csv file to be read
    number_lines = sum(1 for row in (open(in_csv)))

    # size of chunks of data to write to the csv
    chunksize = 10

    # start looping through data writing it to a new file for each chunk
    for i in range(1, number_lines, chunksize):
        df = pd.read_csv(in_csv,
                         header=None,
                         nrows=chunksize,  # number of rows to read at each loop
                         skiprows=i)  # skip rows that have been read

        df.to_csv(out_csv,
                  index=False,
                  header=False,
                  mode='a',  # append data to csv file
                  chunksize=chunksize)  # size of data to append for each loop


def draw_data(x_values, y_values):
    p = figure()
    p.line(x_axis_type="datetime", title="Flex Readings", plot_width=800, plot_height=800)
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_alpha = 0.5
    # p.xaxis.axis_label = 'Times (ms)'
    # p.yaxis.axis_label = 'Value (%)'

    p.line(x=x_values, y=y_values, color='blue', line_width=2)
    output_file('test.html')

    show(p)


def generate_plot(data):

    # try:
    #     data["Time:"] = [datetime.datetime.fromtimestamp(x) for x in data["Time:"]]
    #     data['Time:'] = [x.strftime("%H:%M:%S.{} %p".format(x.microsecond % 100)) for x in data["Time:"]]
    # except TypeError:
    #     pass
    print(data)
    source = ColumnDataSource(data)
    print(source.column_names)
    p = figure(x_axis_type='datetime')
    print(p.line(x='Time:', y='Temp Value:', source=source))
    # p.line(x='Time:', y='Strain Value:', source=source)

    p.plot_width = 800
    p.plot_height = 800
    p.title.text = 'Device Readings'
    p.xaxis.axis_label = 'Time of Reading'
    p.yaxis.axis_label = 'Readings'

    hover = HoverTool()
    hover.tooltips = [
        ('Time of Reading', '@{Time:}{%M:%S.%3N}'),
    ]

    hover.formatters = {"@{Time:}": "datetime"}
    p.add_tools(hover)

    # show(p)

    return p, source


def generate_plot_2():

    data = pd.read_csv('data/streamed_data.csv')
    # data["Time:"] = [datetime.datetime.fromtimestamp(x) for x in data["Time:"]]
    data["Time:"] = [datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f") for x in data["Time:"]]

    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.grid()
    lines = ax.plot(data['Time:'], data['Temp Value:'], color='red')
    lines.append(ax.plot(data['Time:'], data['Strain Value:'], color='blue'))

    ax.set(xlabel='time (s)', ylabel='Analog voltage (mV/1024)',
           title='Device Reading')
    # ax.set_ylim([0, 1024])

    plt.show()


if __name__ == "__main__":
    generate_plot_2()
    print('Plot generated.')
