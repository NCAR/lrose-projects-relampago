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

debug = 1
pastSecs = 86400 * 3
ftpServer = 'ftp.eol.ucar.edu'
ftpUser = 'relampago18'
ftpPasswd = 'gr@N!20'
homeDir = os.getenv('HOME')
gifDir = os.path.join(homeDir, 'soundings/SMN/gifs')
sites = ['COR','MDZ','SIS','VMRS']
#sites = ['SIS']
ftpCatalogServer = 'catalog.eol.ucar.edu'
ftpCatalogUser = 'anonymous'
catalogDestDir = '/pub/incoming/catalog/relampago'
pythonPath = os.getenv('PYTHONPATH')
print >>sys.stderr, "  PYTHONPATH: ", pythonPath

# get current date and time
nowTime = time.gmtime()
now = datetime.datetime(nowTime.tm_year, nowTime.tm_mon, nowTime.tm_mday,
                        nowTime.tm_hour, nowTime.tm_min, nowTime.tm_sec)
nowDateStr = now.strftime("%Y%m%d")
nowDateTimeStr = now.strftime("%Y%m%d%H%M%S")

# compute start time
#pastSecs = int(options.pastSecs)
pastSecs = 108000
pastDelta = timedelta(0, pastSecs)
startTime = now - pastDelta
startDateTimeStr = startTime.strftime("%Y%m%d%H%M%S")
startDateStr = startTime.strftime("%Y%m%d")

# set up list of days to be checked
nDays = (pastSecs / 86400) + 1
dateStrList = []
for iDay in range(0, nDays):
    deltaSecs = timedelta(0, iDay * 86400)
    dayTime = now - deltaSecs
    dateStr = dayTime.strftime("%Y%m%d")
    dateStrList.append(dateStr)

for i in range(0,len(sites)):
    if debug:
        print >>sys.stderr, "Processing ",sites[i]," Data"
    sourceDir = '/sounding/SMN/'+sites[i]
    targetDir = os.path.join(homeDir, 'soundings/SMN/' + sites[i])
    tmpDir = '/tmp/soundings/'+sites[i]
    if not os.path.exists(tmpDir):
        os.makedirs(tmpDir)

    # log into NCAR ftp server and look for new soundings
    ftpFileList = []
    try:
        inFTP = FTP(ftpServer)
        inFTP.set_debuglevel = 2   # verbose
        inFTP.login(ftpUser,ftpPasswd)
        inFTP.cwd(sourceDir)
        ftpFileList = inFTP.nlst()
    except Exception as e:
        print >>sys.stderr, "FTP failed, exception: ", e
        continue

    ftpDateList = []
    for j in range(0,len(ftpFileList)):
        ftpDateList.append('20'+ftpFileList[j][0:6])
    
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
        #ftpDayDir = os.path.join(sourceDir, dateStr)
        #inFTP.cwd(sourceDir)
        #ftpFileList = inFTP.nlst()
        ftpDateList.reverse()
        ftpFileList.reverse()
        if debug:
            print >>sys.stderr, "  ftpDateList: ", ftpDateList
            print >>sys.stderr, "  ftpFileList: ", ftpFileList

        # loop through the ftp file list, downloading those that have
        # not yet been downloaded
        for idx,ftpFileName in enumerate(ftpFileList,0):
            if debug:
                print >>sys.stderr, "  idx = ", idx
                print >>sys.stderr, "  ftpFileName = ", ftpFileName
            if ftpDateList[idx] == dateStr:
                if debug:
                    print >>sys.stderr, " processing ",ftpFileName
                fileTimeStr = ftpFileName[7:9]+'0000'
                fileDateTimeStr = dateStr + fileTimeStr
                #localFileName = dateStr + '_' + ftpFileName
                localFileName = ftpFileName
                if (int(fileDateTimeStr) < int(startDateTimeStr)):
                    if debug:
                        print >>sys.stderr, "  file time too old: ", fileDateTimeStr
                        print >>sys.stderr, "  startDateTimeStr:  ", startDateTimeStr
                else:
                    if (localFileName not in localFileList):
#                    if (True):
                        if debug:
                            print >>sys.stderr, localFileName," not in localFileList -- get file"
                        tmpPath = os.path.join(tmpDir, localFileName)
                        if debug:
                            print >>sys.stderr, " tmpPath = ", tmpPath
                            print >>sys.stderr, " ftpFileName = ", ftpFileName
                        file = open(tmpPath, 'w')
                        if debug:
                            print >>sys.stderr, " Done opening file"

                        try:
                            inFTP.retrbinary('RETR '+ ftpFileName, file.write)
                        except Exception as e:
                            print >>sys.stderr, "FTP RETR failed, exception: ", e
                            continue

                        file.close()
                        if debug:
                            print sys.stderr, "  ftped file to ", tmpPath
                    
                        # Create sounding
                        if debug:
                            print >>sys.stderr, "  creating skewt plot"
                        cmd = 'python -W ignore ' + \
                              homeDir + \
                              '/python/skewplot_relampago.py --filepath ' + \
                              tmpDir + \
                              ' --outpath . --format lst'
                        if debug:
                            print >>sys.stderr, " cmd = ",cmd                        
                        os.system(cmd)
                        #localFileList = os.listdir('.')
                        included_extensions = ['jpg', 'bmp', 'png', 'gif']
                        soundingFiles = [fn for fn in os.listdir('.')
                                         if any(fn.endswith('png') for ext in included_extensions)]
                        soundingFile = "not_yet_set"
                        if len(soundingFiles) != 0:
                            soundingFile = soundingFiles[0]
                        if debug:
                            print >>sys.stderr, \
                                "  Done with skewt -- soundingFile = ", soundingFile

                        # Convert png to gif and remove old png file
                        (soundingPrefix,soundingExt) = os.path.splitext(soundingFile)
                        cmd = 'convert '+soundingPrefix+soundingExt+' '+soundingPrefix+'.gif'
                        os.system(cmd)
                        cmd = 'rm '+soundingFile
                        os.system(cmd)
                        soundingFile = soundingPrefix+'.gif'
 
                        if debug:
                            print >>sys.stderr, \
                                " Done converting to gif -- soundingFile = ", soundingFile

                        # Ftp sounding to catalog
                        if debug:
                            print >>sys.stderr, "  ftp'ing skewt plot to catalog"

                        try:

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

                            # Move text file
                            cmd = "mv " + tmpPath + " ."
                            os.system(cmd)

                        except Exception as e:
                            print >>sys.stderr, "FTP failed, exception: ", e
                            continue

                    else:
                        if debug:
                            print >>sys.stderr, "  File ",ftpFileName," already in catalog"

    # close ftp connection
    inFTP.quit()
    

                              
