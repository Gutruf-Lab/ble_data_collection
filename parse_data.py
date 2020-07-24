#!/usr/bin/env python
import csv
import numpy as np # we will use this later, so import it now
import pandas
from datetime import date
from bokeh.io import output_notebook, output_file, show
from bokeh.plotting import figure




def read_data():
    with open('data/generated_data.csv', 'r') as f:
        csv_reader = csv.DictReader(f)
        line_count = 0

        datetimes = []
        values = []
        iteritems = iter(csv_reader)
        next(csv_reader)
        for row in iteritems:
            datetimes.append(row["Time:"])
            values.append(row["Reading:"])

    return datetimes, values


def draw_data(x_values, y_values):
    output_notebook()
    p = figure(x_axis_type="datetime", title="Flex Readings", plot_width=800, plot_height=800)
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_alpha = 0.5
    p.xaxis.axis_label = 'Times (ms)'
    p.yaxis.axis_label = 'Value (%)'

    p.line(x=x_values, y=y_values, color='blue', line_width=2)
    output_file('test.html')

    show(p)


if __name__ == "__main__":
    x, y = read_data()
    draw_data(x, y)
