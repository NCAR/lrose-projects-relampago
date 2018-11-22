from __future__ import print_function

"""
Before running this script there is a
dependency for reading WMO BUFR:

pip install pybufrkit

This library has a way to work within the python script
but as of now it works using a command line interface.

It is important to download the files from the ftp using binary mode!

This was tested on python 2.7 using operational files

"""


def convert_bufr_hd(bufr_file, path_out=None, VERSION=1):
    """
    This function will parse a WMO BUFR sounding using a
    pure python toolkit: PyBufrKit
    The parsing will be done using a query over the bufr
    using tables included in the package.

    Parameters
    ----------
    bufr_file : str
        Only the bufr file name.

    path_out : str (optional)
        The full path of the out file.

    VERSION : int (optional)
        Which version is used to get the final file name. It could be 1
        that is calculated from the launching time or 2 that is extracted
        from the file header. The default is 2.

    """

    import os
    import sys
    import subprocess
    from datetime import datetime, timedelta

    # This will parse only the WMO station number to check if
    # we have to process the file or return
    region = subprocess.check_output(
        'pybufrkit query 001001 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]
    number = subprocess.check_output(
        'pybufrkit query 001002 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]

    wmo_code = region + number

    if wmo_code == '87344':
        directory = 'COR/'
        print('Reading BUFR {bufr_file}'.format(bufr_file=bufr_file))
        print('The station is {wmo_code}: Cordoba Aero'.format(wmo_code=wmo_code))
    elif wmo_code == '87155':
        directory = 'SIS/'
        print('Reading BUFR {bufr_file}'.format(bufr_file=bufr_file))
        print('The station is {wmo_code}: Resistencia Aero'.format(wmo_code=wmo_code))
    elif wmo_code == '87244':
        directory = 'VMRS/'
        print('Reading BUFR {bufr_file}'.format(bufr_file=bufr_file))
        print('The station is {wmo_code}: Villa Maria del Rio Seco'.format(wmo_code=wmo_code))
    elif wmo_code == '87418':
        directory = 'MDZ/'
        print('Reading BUFR {bufr_file}'.format(bufr_file=bufr_file))
        print('The station is {wmo_code}: Mendoza Aero'.format(wmo_code=wmo_code))
    elif wmo_code == '87576':
        print('The station is {wmo_code}: Ezeiza Aero, do not process'.format(wmo_code=wmo_code))
        print()
        return
    else:
        print('Do not care about station {wmo_code}'.format(wmo_code=wmo_code))
        print()
        return
    if not os.path.exists(path_out+directory):
        os.makedirs(path_out+directory)

    # Now we parse the date and time of the baloon launching
    year = subprocess.check_output(
        'pybufrkit query 004001 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]
    month = subprocess.check_output(
        'pybufrkit query 004002 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]
    day = subprocess.check_output(
        'pybufrkit query 004003 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]
    hour = subprocess.check_output(
        'pybufrkit query 004004 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]
    minute = subprocess.check_output(
        'pybufrkit query 004005 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]
    second = subprocess.check_output(
        'pybufrkit query 004006 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]

    time_of_launch = datetime(int(year),
                              int(month),
                              int(day),
                              int(hour),
                              int(minute),
                              int(second))
    print('The time of launching was: {time_of_launch}'.format(time_of_launch=time_of_launch))

    if VERSION == 1:
        time_of_sounding = datetime(time_of_launch.year,
                                    time_of_launch.month,
                                    time_of_launch.day,
                                    time_of_launch.hour,
                                    0,
                                    0)

        # In order to have the correct output file name we have to check
        # and correct the time of launching.
        # If it is around the hour (5 minutes after and before)
        # we can assume the launching was within
        # an hourly schedule and we are ok with the time_of_sounding being
        # the same as time_of_launch.
        # But as the other soundings (i.e. with regular or tri-hourly schedules)
        # are launched way before the hour we have to add one hour to the
        # time_of_launch.
        # Either way if the sounding was supposed to be 12UTC it may be the case
        # that the time_of_launch still is between

        if (time_of_launch.minute > 5) and (time_of_launch.minute < 55):
            time_of_sounding = time_of_sounding + timedelta(hours=1)

        # if time_of_sounding.hour == 11:
        #     time_of_sounding = time_of_sounding + timedelta(hours=1)
        # elif time_of_sounding.hour == 23:
        #     time_of_sounding = time_of_sounding + timedelta(hours=1)

    elif VERSION == 2:
        year = subprocess.check_output(
            'pybufrkit info {bufr_file} | grep year'.format(bufr_file=bufr_file),
                shell=True).decode().split('\n')[-2].split(' ')[-1]
        month = subprocess.check_output(
            'pybufrkit info {bufr_file} | grep month'.format(bufr_file=bufr_file),
                shell=True).decode().split('\n')[-2].split(' ')[-1]
        day = subprocess.check_output(
            'pybufrkit info {bufr_file} | grep day'.format(bufr_file=bufr_file),
                shell=True).decode().split('\n')[-2].split(' ')[-1]
        hour = subprocess.check_output(
            'pybufrkit info {bufr_file} | grep hour'.format(bufr_file=bufr_file),
                shell=True).decode().split('\n')[-2].split(' ')[-1]
        minute = subprocess.check_output(
            'pybufrkit info {bufr_file} | grep minute'.format(bufr_file=bufr_file),
                shell=True).decode().split('\n')[-2].split(' ')[-1]
        second = subprocess.check_output(
            'pybufrkit info {bufr_file} | grep second'.format(bufr_file=bufr_file),
                shell=True).decode().split('\n')[-2].split(' ')[-1]

        time_of_sounding = datetime(int(year),
                                    int(month),
                                    int(day),
                                    int(hour),
                                    int(minute),
                                    int(second))

    print('The datetime of the file name will be: {time_of_sounding}'.format(time_of_sounding=time_of_sounding))

    file_name = time_of_sounding.strftime('%y%m%d_%H_{wmo_code}.lst'.format(wmo_code=wmo_code))
    # print(file_name)
    # Here we can add the sounding site to the path
    file_name_path = '{path_out}{directory}{file_name}'.format(path_out=path_out,
                                                               directory=directory,
                                                               file_name=file_name)

    if os.path.exists(file_name_path):
        print('Already did {file_name_path}'.format(file_name_path=file_name_path))
        print()
        return

    # pressure in Pa
    pressure = subprocess.check_output(
        'pybufrkit query 007004 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]

    # geopotential height
    height = subprocess.check_output(
        'pybufrkit query 010009 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]

    # Temperature in K
    temp = subprocess.check_output(
        'pybufrkit query 012101 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]

    # Dew point temperature in K
    temp_dew = subprocess.check_output(
        'pybufrkit query 012103 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]

    # Wind direction in degrees
    dir_v = subprocess.check_output(
        'pybufrkit query 011001 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]

    # Wind speed in m/s
    vel_v = subprocess.check_output(
        'pybufrkit query 011002 {bufr_file}'.format(bufr_file=bufr_file), shell=True).decode().split('\n')[-2]

    pressure = [float(x)/100 for x in pressure.split(',')]
    height = [int(x) for x in height.split(',')]
    temp = [round(float(x)-273.15, 2) for x in temp.split(',')]  # convert to Celsius
    temp_dew = [round(float(x)-273.15, 2) for x in temp_dew.split(',')]  # convert to Celsius
    dir_v = [int(x) for x in dir_v.split(',')]
    vel_v = [round(float(x)*1.94384, 4) for x in vel_v.split(',')]  # convert to kt


    print('Starting to write in: {file_name_path}'.format(file_name_path=file_name_path))
    with open('{file_name_path}'.format(file_name_path=file_name_path), 'w') as fid:
        for p, h, t, td, dv, vv in zip(pressure, height, temp, temp_dew, dir_v, vel_v):
            fid.write('\t{p},\t{h},\t{t},\t{td},\t{dv},\t{vv}\n'.format(p=p,
                                                                        h=h,
                                                                        t=t,
                                                                        td=td,
                                                                        dv=dv,
                                                                        vv=vv))

    print('Finished writing the csv')
    print()

#################################################

# Example of usage with glob
# we might move the processed bufr to another directory

# this import needs to happens at the beginning of the file
# from __future__ import print_function

import os
import sys
import glob

# Check input parameters
script = sys.argv[0]
if len(sys.argv) != 3:
    print('Useage: {script} [path_in] [path_out]'.format(script=script))
    quit()

path_in = sys.argv[1]
path_out = sys.argv[2]
print('path_in  = {path_in}'.format(path_in=path_in))
print('path_out = {path_out}'.format(path_out=path_out))

bufr_list = glob.glob('{path_in}/radiosondeos_*'.format(path_in=path_in))

for bufr_file in bufr_list:
    convert_bufr_hd(bufr_file, path_out)
    # then move bufr already processed
    os.rename('{bufr_file}'.format(bufr_file=bufr_file),
              '{path_in}/processed/{bufr_file}'.format(path_in=path_in,
                                                       bufr_file=bufr_file.split("/")[-1]))
