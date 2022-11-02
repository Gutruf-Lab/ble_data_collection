# About

This project is used to process incoming data from a flex sensor on a flexible substrate. Data is streamed using a
virtual serial port through the Bluetooth Low Energy Protocol on a DA14585 chip. Data is stored in a csv file with each
row having two columns: `[milliseconds from Unix Epoch, sensor flex reading]`


Example:

| milliseconds from Unix Epoch | sensor reading (flex %)|
| ----------- | ----------- |
159520268701381900 | 97
1595202687013819001| 85


## Install Instructions
Currently running in Python 3.7
1. Ensure you have the C++ build tools for your OS. Download them here under Tools for Visual Studio.
    - https://visualstudio.microsoft.com/downloads/
2. Clone this repository somewhere onto your system, open the new project directory, and create & activate a virtualenv.
    - `pip install virtualenv`
    - Create the environment: `virtualenv venv`
    - if you have path issues: `python3 -m virtualenv venv`
        - Activate Venv On Windows: `.\venv\Scripts\activate`
        - Activate on Linux: `source /venv/Scripts/activate`
        - Activate on MacOS: `source ./venv/bin/activate`
4. Run command `pip install -r requirements.txt` to install all dependencies.

