# Brody Fuchs, CSU, November 2015
# brfuchs@atmos.colostate.edu


## Update the skewT code to be smarter using classes and what not
# use the KUILsounding.txt as an example or KBMXsounding.txt

# Start out by just plotting the raw data first

import numpy as np
import matplotlib.pyplot as plt
plt.switch_backend('agg')
import skewPy
from skewPy import SkewT
import os
import datetime
import glob
import sys
import argparse

stn_info = {
            '87344': {'longname': 'Cordoba Aerodrome', 'shortname': 'Cordoba_AR', 'lat': -31.297, 'lon': -64.212}, 
            '87418': {'longname': 'Mendoza Aerodrome', 'shortname': 'Mendoza_AR', 'lat': -32.844, 'lon': -68.796},
            '87244': {'longname': 'Villa Maria del Rio Seco', 'shortname': 'Villa_Maria_AR', 'lat': -29.906, 'lon': -63.726},
            '87155': {'longname': 'Resistencia Aerodrome', 'shortname': 'Resistencia_AR', 'lat': -27.446, 'lon': -59.051},


            }


variable_snd_info = {
    
                'M1': {'longname': 'AMF site', 'shortname': 'M1', 'lat': -32.126, 'lon': -64.728},
                'S1': {'longname': 'Villa Dolores', 'shortname': 'S1', 'lat': -31.951, 'lon': -65.149}

}


# Cordoba: -31.296639, -64.211855
# Mendoza: -32.843745, -68.796345
# Rio Seco: -29.90637, -63.72592


file_in_dt_fmt = '%y%m%d_%H'
file_out_dt_fmt = '%Y%m%d%H%M'
title_dt_fmt = '%Y%m%d %H00Z'

file_in_dt_fmt_edt = '%Y%m%d.%H%M'


parser = argparse.ArgumentParser(description='Put in a file to be processed')

#parser.add_argument('--noarg', action="store_true", default=False)
parser.add_argument('--file', action="store", dest="file", default=None)

# location of sounding files
parser.add_argument('--filepath', action='store', dest='filepath', default='.')
# where you want to output skewTs
parser.add_argument('--outpath', action='store', dest='outpath', default='.')
# the first part of the sounding raw data file, need it to search for possible files
                    # other possibilities are 'K' for K*** UWYO soundings, could also be 'EDT' for Vaisala soundings
parser.add_argument('--prefix', action="store", dest="prefix", default='')
# This can currently be 'EC' for Canadian format, 'UWYO' for Wyoming soundings or 'EDT' for Vaisala CSU soundings
# Or XML, so some dumb*** reason. Gave us something to do on the SPURS2 cruise, I suppose
parser.add_argument('--format', action='store', dest='format', default='XML')
# put this in if want to override the station name in the title of the skewT, default is fmt above
                                    # otherwise just put None
parser.add_argument('--station', action='store', dest='station', default=None)
# turning this switch on will just print more stuff, maybe needed if trying to debug
parser.add_argument('--debug', action='store', dest='debug', type=int, default=0)
# This will process a certain file in the filepath. The number will correspond to the index of the file
parser.add_argument('--number', action='store', dest='number', default=None)
# This will process the last file in the filepath
parser.add_argument('--last', action='store', dest='last', default=None)


pargs = parser.parse_args()



##### PARAMETERS YOU CAN CHANGE HERE #########

# file_path = 'Data/soundings/' 
# out_path = 'Images/soundings/' 
# prefix = 'Revelle' # the first part of the sounding raw data file, need it to search for possible files
#                     # other possibilities are 'K' for K*** UWYO soundings, could also be 'EDT' for Vaisala soundings
# fmt = 'XML' 
# station_name = None # put this in if want to override the station name in the title of the skewT, default is fmt above
#                                     # otherwise just put None

########### DON'T NEED TO WORRY ABOUT ANYTHING BELOW HERE ############


if pargs.file is not None:
   	sounding_files = [pargs.file]

elif pargs.filepath is not None:
    sounding_files = sorted(glob.glob('%s/%s*%s'%(pargs.filepath, pargs.prefix, pargs.format)))

else: 
    sounding_files = sorted(glob.glob('%s/*'%(pargs.filepath)))


print 'processing the following files: {}'.format(sounding_files)



for fname in sounding_files:
    #file_title = os.path.basename(fname)[4:-4]

    fbase = os.path.basename(fname)

    print 'Processing %s'%os.path.basename(fbase)
    # this next part is going to be RELAMPAGO specific
    # the files look like they're coming in the format of YYMMDD_HH_STN.lst
    # so need to parse that

    ##file_title = os.path.basename(fname)[:-4]

    if pargs.format == 'lst':
        file_time_string = fbase[:9]

        file_time = datetime.datetime.strptime(file_time_string, file_in_dt_fmt)

        stn_id = fbase[10:15]
        si = stn_info[stn_id]
        print 'Station: {}'.format(si['shortname'])

        out_fname = 'upperair.SkewT.{date}.{site}.png'.format(date=file_time.strftime(file_out_dt_fmt), site=si['shortname'])


        figtitle = '{stn} {ln} {t} sounding ({lat:.3f}, {lon:.3f})'.format(stn=stn_id, ln=si['longname'], t=file_time.strftime(title_dt_fmt),
                                                    lat=si['lat'], lon=si['lon'])


    elif pargs.format == 'EDT' or pargs.format == 'raw':



        dash_ind = fbase.index('-')

        snd_id = fbase[dash_ind+4:dash_ind+6]


        si = variable_snd_info[snd_id]



        file_snd_id = fbase[:14]
        file_time_string = fbase[15:28]
        file_time = datetime.datetime.strptime(file_time_string, file_in_dt_fmt_edt)
        #out_fname = '{fsi}.{dt}.png'.format(fsi=file_snd_id, dt=file_time.strftime(file_out_dt_fmt))
        out_fname = 'upperair.DOE_{sn}_sonde.{dt}.skewT.png'.format(fsi=file_snd_id, sn=si['shortname'], dt=file_time.strftime(file_out_dt_fmt))
        figtitle = '{sn} {ln} {dt} sounding ({lat:.3f}, {lon:.3f})'.format(sn=si['shortname'], ln=si['longname'], 
                            dt=file_time.strftime(title_dt_fmt), lat=si['lat'], lon=si['lon'])




    S = SkewT.Sounding(fname, fmt=pargs.format, station_name=pargs.station, flip_barb=True)

    S.plot_skewt(parcel=True, parcel_draw=True, title=figtitle)
    S.cape()

    # The filenames are made this way to follow the project catalog convention
    plt.savefig('%s/%s'%(pargs.outpath, out_fname), dpi=120)
    plt.close('all')










