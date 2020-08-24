#!/usr/bin/env python
import csv
import numpy as np # we will use this later, so import it now
import pandas as pd
from datetime import date
from bokeh.models import ColumnDataSource
from bokeh.models.tools import HoverTool
from bokeh.plotting import figure, output_file, show
from bleak import BleakClient


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


if __name__ == "__main__":
    data = pd.read_csv('data/generated_data.csv')
    print(data)
    source = ColumnDataSource(data)
    p = figure()
    p.line(x='Time:', y='Reading:', source=source)

    p.plot_width = 800
    p.plot_height = 800
    p.title.text = 'Temperature Readings'
    p.xaxis.axis_label = 'Time of Reading'
    p.yaxis.axis_label = 'Readings'

    hover = HoverTool()
    hover.tooltips = [
        ('Time of Reading', '@Time:'),
        ('Reading Value', '@Reading:'),
    ]
    p.add_tools(hover)

    show(p)
