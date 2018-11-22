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

#nowTime = time.gmtime()
#now = datetime.datetime(nowTime.tm_year, nowTime.tm_mon, nowTime.tm_mday,
#                        nowTime.tm_hour, nowTime.tm_min, nowTime.tm_sec)
#date = now.strftime("%Y_%m_%d")
#date = '2018_11_01'

url = 'https://engineering.arm.gov/~radar/amf1_csapr2_incoming_images/hsrhi/'+date+'/'
ext = 'png'
outDir = '/home/storm/relops/radar/csapr2/'+date
category = 'radar'
platform = 'DOE_CSapr2'
ftpCatalogServer = 'catalog.eol.ucar.edu'
ftpCatalogUser = 'anonymous'
catalogDestDir = '/pub/incoming/catalog/relampago'
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
    (fdate,ftime) = parts[3].split('-')
    fhour = ftime[0:2]
    if fdate == dateNoHyphens and fhour == hour: 
        print file
        cmd = 'wget '+file
        os.system(cmd)

# correct names of -0.0 files
#cmd = 'mmv "*_-0.0.png" "#1_00.0.png"'
#os.system(cmd)

# rename files and ftp them
for file in os.listdir(outDir):
    if file.startswith('cor_'):
        if debug:
            print >>sys.stderr, "file = ",file
        (filename, file_ext) = os.path.splitext(file)
        parts = filename.split('_')
        (date,time) = parts[3].split('-')
        angle_parts = parts[5].split('.')
        if len(angle_parts[0]) == 1:
            angle = '00'+angle_parts[0]
        elif len(angle_parts[0]) == 2:
            angle = '0'+angle_parts[0]
        else:
            angle = angle_parts[0]
        product = parts[2]+'_'+parts[4]+'_'+angle
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




    





