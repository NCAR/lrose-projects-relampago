#!/usr/bin/python

import os
import glob
from shutil import copyfile
from ftplib import FTP

indir = '/home/disk/data/images/ltng_'
regions = ['argentina','samerica']

for i in range(0,len(regions)):
    # find newest file
    list_of_files = glob.glob(indir+regions[i]+'/*')
    latest_file = max(list_of_files, key=os.path.getctime)
    #print regions[i]
    #print latest_file
    
    # extract date_time from latest_file & create catalog filename
    path,filename = os.path.split(latest_file)
    tmp = filename.split('_')
    date_time = tmp[0]
    latest_file_new = 'satellite.GOES_Plus_WWLLN.'+date_time+'.'+regions[i]+'.gif'
    #print latest_file_new

    # copy and rename file
    copyfile(latest_file,'/tmp/'+latest_file_new)

    # ftp file to NCAR server
    os.chdir('/tmp')
    myFTP = FTP('catalog.eol.ucar.edu','anonymous')
    #myFTP = FTP('catalog.eol.ucar.edu','anonymous','brodzik@uw.edu')
    myFTP.cwd('/pub/incoming/catalog/relampago')
    file = open(latest_file_new,'rb')
    #myFTP.storbinary('STOR %s',file)
    myFTP.storbinary('STOR '+latest_file_new,file)
    file.close()
    myFTP.quit()

    # remove file copy from /tmp
    os.remove('/tmp/'+latest_file_new)

                              
