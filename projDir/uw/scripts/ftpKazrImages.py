#!/usr/bin/python

import sys
import os
import time
import datetime
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
from ftplib import FTP

#if len(sys.argv) != 2:
#    print >>sys.stderr, "Useage: ",sys.argv[0]," [YYYY_MM_DD]"
#    quit()
#date = sys.argv[1]

# get current date and time minus one hour
UTC_OFFSET_TIMEDELTA = datetime.datetime.utcnow() - datetime.datetime.now()
date_1_hour_ago = datetime.datetime.now() - timedelta(hours=1) + UTC_OFFSET_TIMEDELTA
date = date_1_hour_ago.strftime("%Y_%m_%d")
dateNoHyphens = date_1_hour_ago.strftime("%Y%m%d")
hour = date_1_hour_ago.strftime("%H")

url = 'https://engineering.arm.gov/~radar/amf1_kazr_incoming_images/'+date+'/'
ext = 'png'
outDir = '/home/storm/relops/radar/kazr/'+date
category = 'radar'
platform = 'DOE_KAZR'
ftpCatalogServer = 'catalog.eol.ucar.edu'
ftpCatalogUser = 'anonymous'
catalogDestDir = '/pub/incoming/catalog/relampago'
burstMode = 'kazrcfrge'
debug = 1

def listFD(url, ext=''):
    page = requests.get(url).text
    print page
    soup = BeautifulSoup(page, 'html.parser')
    return [url + '/' + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]

if not os.path.exists(outDir):
    os.makedirs(outDir)
os.chdir(outDir)

for file in listFD(url, ext):
    tmp = os.path.basename(file)
    (f,e) = os.path.splitext(tmp)
    parts = f.split('_')
    mode = parts[1]
    (fdate,ftime) = parts[2].split('-')
    fhour = ftime[0:2]
    if fdate == dateNoHyphens and fhour == hour and mode == burstMode: 
        print file
        cmd = 'wget '+file
        os.system(cmd)

# rename files and ftp them
for file in os.listdir(outDir):
    if file.startswith('cor_'):
        if debug:
            print >>sys.stderr, "file = ",file
        (filename, file_ext) = os.path.splitext(file)
        parts = filename.split('_')
        (date,time) = parts[2].split('-')
        product = parts[3]+'_burst_mode'
        file_cat = category+'.'+platform+'.'+date+time+'.'+product+file_ext
        if debug:
            print >>sys.stderr, "file_cat = ",file_cat
        cmd = 'mv '+file+' '+file_cat
        os.system(cmd)
    
        # ftp file
        catalogFTP = FTP(ftpCatalogServer,ftpCatalogUser)
        catalogFTP.cwd(catalogDestDir)
        file = open(file_cat,'rb')
        catalogFTP.storbinary('STOR '+file_cat,file)
        file.close()
        catalogFTP.quit()



    





