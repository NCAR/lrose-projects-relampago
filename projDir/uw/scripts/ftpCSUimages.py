#!/usr/bin/python

import os
import sys
#import glob
#from shutil import copyfile
from ftplib import FTP
import time
import datetime
from datetime import timedelta
import subprocess
import paramiko

def find_nth(string, substring, n):
    if (n == 1):
        return string.find(substring)
    else:
        return string.find(substring, find_nth(string, substring, n - 1) + 1)

# User inputs
debug = 0
secsPerDay = 86400
pastSecs = 108000
ncarServer = '192.168.1.40'
ncarUser = 'relamp'
ncarPasswd = 'relamp18!!'
ncarSourceDirBase = '/data/relamp/data.server/relampago/cfradial/CSU_CHIVO/radar_data/figures'
targetDirBase = '/home/storm/relops/radar/CSU_CHIVO'
tmpDir = '/tmp/CSU_CHIVO'
imageTypes = ['cappi','rain','raw_ppi','volume']
prodNames_raw = ['variables','rraccum','ppi_sweep0','ppi']
prodNames = ['cappi_2km_6vars','rain','ppi_qc_level0_6vars','ppi_qc_refl_allElevs']
ftpCatalogServer = 'catalog.eol.ucar.edu'
ftpCatalogUser = 'anonymous'
catalogDestDir = '/pub/incoming/catalog/relampago'

# check for tmpDir
if not os.path.exists(tmpDir):
    os.makedirs(tmpDir)

# get current date and time
nowTime = time.gmtime()
now = datetime.datetime(nowTime.tm_year, nowTime.tm_mon, nowTime.tm_mday,
                        nowTime.tm_hour, nowTime.tm_min, nowTime.tm_sec)
nowDateStr = now.strftime("%Y%m%d")
nowDateTimeStr = now.strftime("%Y%m%d%H%M%S")

# compute start time
pastDelta = timedelta(0, pastSecs)
startTime = now - pastDelta
startDateTimeStr = startTime.strftime("%Y%m%d%H%M%S")
startDateStr = startTime.strftime("%Y%m%d")

# set up list of days to be checked
nDays = (pastSecs / secsPerDay) + 1
dateStrList = []
for iDay in range(0, nDays):
    deltaSecs = timedelta(0, iDay * secsPerDay)
    dayTime = now - deltaSecs
    dateStr = dayTime.strftime("%Y%m%d")
    dateStrList.append(dateStr)
if debug:
    print sys.stderr, "dateStrList: ", dateStrList

for idx,image in enumerate(imageTypes,0):
    if debug:
        print >>sys.stderr, "Processing ",image," data"
    ncarSourceDir = ncarSourceDirBase+'/'+image
    targetDir = targetDirBase+'/'+image
    if not os.path.exists(targetDir):
        os.makedirs(targetDir)

    # log into NCAR server and look for new images
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy( paramiko.AutoAddPolicy() )
    ssh.connect(ncarServer, username=ncarUser, password=ncarPasswd)
    ftp = ssh.open_sftp()
    ftpDateList = ftp.listdir(ncarSourceDir)
    ftpDateList.sort()
    ftpDateList.reverse()
    if debug:
        print >>sys.stderr, "ftpDateList: ", ftpDateList

    # loop through days
    for dateStr in dateStrList:
        if debug:
            print >>sys.stderr, "dateStr = ", dateStr
        if (dateStr not in ftpDateList):
            if debug:
                print >>sys.stderr, "  WARNING: ignoring date, does not exist on ftp site"
            continue

        # make the target dir and cd to it
        localDayDir = os.path.join(targetDir, dateStr)
        if not os.path.exists(localDayDir):
            os.makedirs(localDayDir)

        # get local file list - i.e. those which have already been downloaded
        os.chdir(localDayDir)
        localFileList = os.listdir('.')
        localFileList.reverse()
        if debug:
            print >>sys.stderr, "  localFileList: ", localFileList

        # get ftp server file list, for day dir
        ftpDayDir = os.path.join(ncarSourceDir, dateStr)
        ftpTmpList = ftp.listdir(ftpDayDir)
        ftpFileList = []
        for tmpFile in ftpTmpList:
            if prodNames_raw[idx] in tmpFile:
                ftpFileList.append(tmpFile)
        ftpFileList.reverse()
        if debug:
            print >>sys.stderr, "  ftpFileList: ", ftpFileList

        # loop through the ftp file list, downloading those that have
        # not yet been downloaded
        for ftpFileName in ftpFileList:
            if debug:
                print >>sys.stderr, "  ftpFileName = ", ftpFileName
            fileTimeStr = ftpFileName[12:18]
            fileDateTimeStr = dateStr + fileTimeStr
            localFileName = ftpFileName
            if (int(fileDateTimeStr) < int(startDateTimeStr)):
                if debug:
                    print >>sys.stderr, "    file time = ", fileDateTimeStr, " too old for startDateTimeStr = ", startDateTimeStr
            else:
                if (localFileName not in localFileList):
                    if debug:
                        print >>sys.stderr, "    localFileName = ", localFileName, " NOT in localFileList = ", localFileList
                    ftpFileNameFull = ftpDayDir+'/'+ftpFileName
                    localFileNameFull = localDayDir+'/'+ftpFileName
                    ftp.get(ftpFileNameFull,localFileNameFull)
                    if debug:
                        print sys.stderr, "    ftped file to ", localDayDir
                    
                    #copy/rename file to tmpDir
                    (ftpFileNamePrefix,ftpFileNameExt) = os.path.splitext(ftpFileName)
                    if imageTypes[idx] == 'raw_ppi':
                        (datePlus,time,junk1,junk2) = ftpFileNamePrefix.split('_')
                    else:
                        (datePlus,time,junk) = ftpFileNamePrefix.split('_')
                    date = datePlus[3:]
                    newFileName = 'radar.CSU_CHIVO.'+date+time+'.'+prodNames[idx]+ftpFileNameExt
                    newFileNameFull = tmpDir+'/'+newFileName
                    cmd = 'cp '+localFileNameFull+' '+newFileNameFull
                    if debug:
                        print >>sys.stderr, "    cmd = ", cmd
                    os.system(cmd)
                    
                    #ftp to catalog
                    catalogFTP = FTP(ftpCatalogServer,ftpCatalogUser)
                    catalogFTP.cwd(catalogDestDir)
                    if debug:
                        print >>sys.stderr, "    ftp'ing newFileNameFull = ", newFileNameFull
                    file = open(newFileNameFull,'rb')
                    catalogFTP.storbinary('STOR '+newFileName,file)
                    file.close()
                    catalogFTP.quit()
                    
                    #remove file from tmpDir
                    cmd = '/bin/rm '+tmpDir+'/'+newFileName
                    if debug:
                        print >>sys.stderr, "    cmd = ", cmd
                    os.system(cmd)
                else:
                    if debug:
                        print >>sys.stderr, "    localFileName = ", localFileName, " in localFileList = ", localFileList

    # close sftp connection
    ftp.close()
    ssh.close()
    






    

                              
