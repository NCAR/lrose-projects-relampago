#!/usr/bin/python

import os
import sys
from ftplib import FTP
import time
import datetime
from datetime import timedelta
import subprocess

# User inputs
debug = 1
secsPerDay = 86400
#pastSecs = 108000
pastSecs = 518400
ftpServer = 'ftp.eol.ucar.edu'
ftpUser = 'relampago18'
ftpPasswd = 'gr@N!20'
sourceDirBase = '/sounding'
targetDirBase = '/home/storm/relops/soundings/Brazil'
sites = ['Santa_Maria','Sao_Borja','Uruguaiana']
gifDir = targetDirBase+'/gifs'
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
    sourceDir = sourceDirBase+'/'+sites[i]
    targetDir = targetDirBase+'/'+sites[i]
    if not os.path.exists(targetDir):
        os.makedirs(targetDir)

    # log into NCAR ftp server and look for new soundings
    myFTP = FTP(ftpServer)
    myFTP.login(ftpUser,ftpPasswd)
    myFTP.cwd(sourceDir)
    tmpFileList = myFTP.nlst()
    ftpFileList = []
    for file in tmpFileList:
        if file.endswith('.txt') or file.endswith('.png'):
            ftpFileList.append(file)

    # Filename patterns:
    # for Santa Maria:
    #   SBSM2018110112PTU.txt
    #   SBSM2018110112WIND.txt
    #   SBSM_20181101_12.png
    # for Sao Borja:
    #   SBRJ_20181101_12.png
    #   SBRJ_20181101_12.txt
    # for Uruguaiana
    #   18110112_SBUG.png

    ftpDateList = []
    ftpDateTimeList = []
    for ftpFile in ftpFileList:
        if debug:
            print >>sys.stderr, "ftpFile = ", ftpFile
        if ftpFile.endswith('.txt'):
            if sites[i] == 'Santa_Maria':
                if debug:
                    print >>sys.stderr, "  Santa_Maria text file"
                ftpDateList.append(ftpFile[4:12])
                ftpDateTimeList.append(ftpFile[4:14]+'0000')
            elif sites[i] == 'Sao_Borja':
                if debug:
                    print >>sys.stderr, "  Sao_Borja text file"
                ftpDateList.append(ftpFile[5:13])
                ftpDateTimeList.append(ftpFile[5:13]+ftpFile[14:16]+'0000')
            elif sites[i] == 'Uruguaiana':
                if debug:
                    print >>sys.stderr, "  Uruguaiana text file"
        elif ftpFile.endswith('.png'):
            if sites[i] == 'Santa_Maria':
                if debug:
                    print >>sys.stderr, "  Santa_Maria image file"
                ftpDateList.append(ftpFile[5:13])
                ftpDateTimeList.append(ftpFile[5:13]+ftpFile[14:16]+'0000')
            elif sites[i] == 'Sao_Borja':
                if debug:
                    print >>sys.stderr, "  Sao_Borja image file"
                ftpDateList.append(ftpFile[5:13])
                ftpDateTimeList.append(ftpFile[5:13]+ftpFile[14:16]+'0000')
            elif sites[i] == 'Uruguaiana':
                if debug:
                    print >>sys.stderr, "  Uruguaiana image file"
                ftpDateList.append('20'+ftpFile[0:6])
                ftpDateTimeList.append('20'+ftpFile[0:8]+'0000')
            
    if debug:
        print >>sys.stderr, "ftpFileList = ", ftpFileList
        print >>sys.stderr, "ftpDateList = ", ftpDateList
        print >>sys.stderr, "ftpDateTimeList = ", ftpDateTimeList

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
        localFileList = os.listdir(localDayDir)
        localFileList.reverse()
        if debug:
            print >>sys.stderr, "  localFileList: ", localFileList

        # get ftp server file list, for day dir
        ftpFileList.reverse()
        ftpDateList.reverse()
        ftpDateTimeList.reverse()
        if debug:
            print >>sys.stderr, "  ftpFileList: ", ftpFileList
            print >>sys.stderr, "  ftpDateList: ", ftpDateList
            print >>sys.stderr, "  ftpDateTimeList: ", ftpDateTimeList

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

                ftpDateTimeStr = ftpDateTimeList[idx]
                localFileName = ftpFileName
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
                        tmpPath = os.path.join(localDayDir+'/'+ftpFileName)
                        file = open(tmpPath, 'wb')
                        myFTP.retrbinary('RETR '+ localFileName, file.write)
                        file.close()
                        if localFileName.endswith('.png'):
                            #rename file
                            file_cat = 'upperair.SkewT.'+ftpDateTimeStr+'.'+sites[i]+'_BR.png'
                            cmd = 'cp '+localFileName+' '+file_cat
                            if debug:
                                print >>sys.stderr, "  cmd = ", cmd
                            os.system(cmd)

                            #ftp to catalog
                            print >>sys.stderr, "  ftp'ing skewt plot"
                            catalogFTP = FTP(ftpCatalogServer,ftpCatalogUser)
                            catalogFTP.cwd(catalogDestDir)
                            tmpFile = localDayDir+'/'+file_cat
                            file = open(tmpFile,'rb')
                            catalogFTP.storbinary('STOR '+file_cat,file)
                            file.close()
                            catalogFTP.quit()
 
                            #move to gifs directory
                            cmd = "mv " + file_cat + ' ' + gifDir
                            print >>sys.stderr, "  cmd = ", cmd
                            os.system(cmd)
 
                    else:
                        print >>sys.stderr, "  File ",ftpFileName," already in catalog"
            
    # close ftp connection
    myFTP.quit()
    
   

                              
