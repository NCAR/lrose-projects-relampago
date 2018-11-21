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
doeServer = 'research-amfc1.amf.arm.gov'
doeUser = 'avarble'
doePasswd = 'science1992arm'
doeSourceDirBase = '/data/collection/cor'
targetDirBase = '/home/storm/relops/soundings/DOE'
sites = ['corsondeM1.00','corsondeS1.00']
suffix = ['curM1','curS1']
gifDir = '/home/storm/relops/soundings/DOE/gifs'
ftpCatalogServer = 'catalog.eol.ucar.edu'
ftpCatalogUser = 'anonymous'
catalogDestDir = '/pub/incoming/catalog/relampago'

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

for i in range(0,len(sites)):
    if debug:
        print >>sys.stderr, "Processing ",sites[i]," Data"
    doeSourceDir = doeSourceDirBase+'/'+sites[i]
    targetDir = targetDirBase+'/'+sites[i]
    if not os.path.exists(targetDir):
        os.makedirs(targetDir)

    # log into DOE server and look for new soundings
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy( paramiko.AutoAddPolicy() )
    ssh.connect(doeServer, username=doeUser, password=doePasswd)
    ftp = ssh.open_sftp()
    ftpFileList = []
    ftpDateList = []
    ftpDateTimeList = []
    for file in ftp.listdir(doeSourceDir):
        if file.endswith('.raw'):
            if suffix[i] in file:
                print file
                ftpFileList.append(file)
                idx1 = find_nth(file,suffix[i],1)
                idx2 = find_nth(file,'.raw',2)
                (junk,date,time) = file[idx1+len(suffix[i]):idx2].split('.')
                ftpDateList.append(date)
                ftpDateTimeList.append(date+time)

    if debug:
        print >>sys.stderr, "ftpFileList = ", ftpFileList
        print >>sys.stderr, "ftpDateList = ", ftpDateList
    
    # loop through days
    count = 0
    for dateStr in dateStrList:
        if (dateStr not in ftpDateList):
            if debug:
                print >>sys.stderr, "WARNING: ignoring date, does not exist on ftp site"
                print >>sys.stderr, "  dateStr: ", dateStr
            continue

        if debug:
            print >>sys.stderr, " dateStr = ", dateStr
        
        # make target directory
        localDayDir = os.path.join(targetDir, dateStr)
        if not os.path.exists(localDayDir):
            os.makedirs(localDayDir)
        os.chdir(localDayDir)
        if debug:
            print >>sys.stderr, "  localDayDir = ", localDayDir

        # get local file list - i.e. those which have already been downloaded
        localFileList = os.listdir('.')
        localFileList.reverse()
        if debug:
            print >>sys.stderr, "  localFileList: ", localFileList

        # get ftp server file list, for day dir
        ftpFileList.sort()
        ftpFileList.reverse()
        ftpDateList.sort()
        ftpDateList.reverse()
        ftpDateTimeList.sort()
        ftpDateTimeList.reverse()
        if debug:
            print >>sys.stderr, "  ftpDateList: ", ftpDateList
            print >>sys.stderr, "  ftpFileList: ", ftpFileList

        # loop through the ftp file list, downloading those that have
        # not yet been downloaded
        if debug:
            print >>sys.stderr, "Starting to loop through ftp file list"
        for idx,ftpFileName in enumerate(ftpFileList,0):
            if debug:
                print >>sys.stderr, "  idx = ", idx
                print >>sys.stderr, "  ftpFileName = ", ftpFileName
                print >>sys.stderr, "  ftpDateList[",idx,"] = ", ftpDateList[idx]
                print >>sys.stderr, "  dateStr = ", dateStr
            if ftpDateList[idx] == dateStr:
                if debug:
                    print >>sys.stderr, " ftpDateList[idx]=dateStr: processing ",ftpFileName

                ftpDateTimeStr = ftpDateTimeList[idx]+'00'
                index = find_nth(ftpFileName,'corsonde',2)
                localFileName = ftpFileName[index:]
                if debug:
                    print >>sys.stderr, "  ftpDateTimeStr = ", ftpDateTimeStr
                    print >>sys.stderr, "  localFileName = ", localFileName
                    print >>sys.stderr, "  int(ftpDateTimeStr) = ", int(ftpDateTimeStr)
                    print >>sys.stderr, "  int(startDateTimeStr) = ", int(startDateTimeStr)
                if (int(ftpDateTimeStr) < int(startDateTimeStr)):
                    if debug:
                        print >>sys.stderr, "  int(ftpDateTimeStr) < int(startDateTimeStr)"
                        print >>sys.stderr, "    file time too old: ", ftpDateTimeStr
                        print >>sys.stderr, "    startDateTimeStr:  ", startDateTimeStr
                else:
                    if debug:
                        print >>sys.stderr, "  int(ftpDateTimeStr) >= int(startDateTimeStr)"
                        print >>sys.stderr, "    file time okay :  ", ftpDateTimeStr
                        print >>sys.stderr, "    startDateTimeStr: ", startDateTimeStr
                        print >>sys.stderr, "    localFileName:    ", localFileName
                        print >>sys.stderr, "    localFileList:    ", localFileList
                    if (localFileName not in localFileList):
                        if debug:
                            print >>sys.stderr, localFileName," not in localFileList -- get file"
                        doeSourceFile = doeSourceDir+'/'+ftpFileName
                        index = find_nth(ftpFileName,'corsonde',2)
                        localFile = localDayDir+'/'+ftpFileName[index:]
                        if debug:
                            print >>sys.stderr, "  doeSourceFile = ", doeSourceFile
                            print >>sys.stderr, "  localFile     = ", localFile
                        ftp.get(doeSourceFile,localFile)

                        if debug:
                            print sys.stderr, "  ftped file to ", localDayDir
                    
                        # Create sounding
                        if debug:
                            print >>sys.stderr, "  creating skewt plot"
                        cmd = 'python -W ignore /home/storm/brodzik/python/brody/skewplot_relampago.py --file '+localFile+' --outpath '+localDayDir+' --format raw'
                        if debug:
                            print >>sys.stderr, " cmd = ",cmd                        
                        os.system(cmd)
                        included_extensions = ['jpg', 'bmp', 'png', 'gif']
                        soundingFiles = [fn for fn in os.listdir(localDayDir)
                                         if any(fn.endswith('png') for ext in included_extensions)]
                        if len(soundingFiles) != 0:
                            soundingFile = soundingFiles[0]
                        else:
                            print >>sys.stderr, "  soundingFile not found . . . stop"
                            sys.exit()
                        if debug:
                            print >>sys.stderr, "  Done with skewt -- soundingFile = ", soundingFile

                        # Ftp sounding to catalog
                        if debug:
                            print >>sys.stderr, "  ftp'ing skewt plot to catalog"
                        catalogFTP = FTP(ftpCatalogServer,ftpCatalogUser)
                        catalogFTP.cwd(catalogDestDir)
                        soundingPath = os.path.join(localDayDir,soundingFile)
                        if debug:
                            print >>sys.stderr, "  soundingPath = ", soundingPath
                        file = open(soundingPath,'rb')
                        catalogFTP.storbinary('STOR '+soundingFile,file)
                        file.close()
                        catalogFTP.quit()
                        if debug:
                            print >>sys.stderr, "  done ftp'ing skewt plot to catalog"
                    
                        # Move skewt file
                        cmd = "mv " + soundingFile + ' ' + gifDir
                        os.system(cmd)
                        if debug:
                            print >>sys.stderr, "  done ftp'ing skewt plot to ", gifDir
                    else:
                        if debug:
                            print >>sys.stderr, "  File ",ftpFileName," already in catalog"
            else:
                if debug:
                    print >>sys.stderr, "  Nothing done . . . ftpDateList[idx] != dateStr"
                    print >>sys.stderr, "    ftpDateList[idx] = ", ftpDateList[idx]
                    print >>sys.stderr, "    dateStr = ", dateStr
                        
    # close sftp connection
    ftp.close()
    ssh.close()
    






    

                              
