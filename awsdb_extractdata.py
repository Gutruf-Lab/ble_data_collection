import pandas as pd
import numpy
import json
from json import JSONDecodeError
from datetime import datetime as dt

raw_data = pd.read_csv('output_09_20.csv')
out_data = pd.DataFrame(raw_data.values)
out_data = out_data.drop([1], axis=1)

for i, entry in enumerate(out_data[0]):
    try:
        out_data.at[i, 0] = json.loads(entry)['indicated_value']
    except JSONDecodeError:
        entry = ''

for d, entry in enumerate(out_data[0]):
    try:
        out_data[0][d] = ' '.join([entry[i:i + 4] for i in range(0, len(entry), 4)])
    except JSONDecodeError:
        pass
    except TypeError:
        pass

for i, entry in enumerate(out_data[2]):
    try:
        out_data.at[i, 3] = dt.fromtimestamp(entry/1000, tz=None)
    except OSError:
        pass
    except ValueError:
        pass

out_data.drop(out_data.tail(2).index, inplace=True)
out_data.to_csv('formatted_data_09_20.csv', index=False, header=False)
