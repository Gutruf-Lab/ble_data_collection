import pandas as pd

file_name = "data/8_18_TuckerTest.csv"
file_name_output = "data/8_18_TuckerTest_nodupes.csv"

df = pd.read_csv(file_name, sep=",")

# Notes:
# - the `subset=None` means that every column is used
#    to determine if two rows are different; to change that specify
#    the columns as an array
# - the `inplace=True` means that the data structure is changed and
#   the duplicate rows are gone
df.drop_duplicates(subset=['Device Timestamp:'], inplace=True)

# Write the results to a different file
df.to_csv(file_name_output, index=False, encoding='utf-8')