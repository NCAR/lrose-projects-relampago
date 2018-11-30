#!/usr/bin/env python

#=====================================================================
#
# Obtain SMA sounding files from ftp site
# Create SkewT plot as image
# Upload SkewT to catalog
#
#=====================================================================

#!/usr/bin/python

import os
import sys
from ftplib import FTP
import time
import datetime
from datetime import timedelta
import subprocess

def main():

    global debug, pastSecs
    global ftpServer, ftpUser, ftpPasswd
    global homeDir, gifDir
    global sites
    global ftpCatalogServer, ftpCatalogUser
    global startDateTimeStr, startDateStr

    debug = True
    pastSecs = 86400 * 3
    ftpServer = 'ftp.eol.ucar.edu'
    ftpUser = 'relampago18'
    ftpPasswd = 'gr@N!20'
    homeDir = os.getenv('HOME')
    gifDir = os.path.join(homeDir, 'soundings/SMN/gifs')
    ftpCatalogServer = 'catalog11.eol.ucar.edu'
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

    # sites = ['COR','MDZ','SIS','VMRS']
    sites = ['VMRS']
    for site in sites:
        processSite(site, dateStrList)

########################################################################
# Process a given site

def processSite(site, dateStrList):

    if debug:
        print >>sys.stderr, "Processing site ", site

    # make tmp dir

    tmpDir = '/tmp/soundings/' + site
    if not os.path.exists(tmpDir):
        os.makedirs(tmpDir)

    sourceDir = '/sounding/SMN/' + site
    targetDir = os.path.join(homeDir, 'soundings/SMN/' + site)

    # log into NCAR ftp server and look for new soundings

    ftpFileList = []
    global inFTP
    try:
        inFTP = FTP(ftpServer)
        inFTP.set_debuglevel = 2   # verbose
        inFTP.login(ftpUser, ftpPasswd)
        inFTP.cwd(sourceDir)
        ftpFileList = inFTP.nlst()
    except Exception as e:
        print >>sys.stderr, "FTP failed, exception: ", e
        return

    ftpDateList = []
    for ftpFile in ftpFileList:
        ftpDateList.append('20' + ftpFile[0:6])
    
    # reverse the order of the lists
    ftpDateList.reverse()
    ftpFileList.reverse()
    if debug:
        print >>sys.stderr, "  ftpDateList: ", ftpDateList
        print >>sys.stderr, "  ftpFileList: ", ftpFileList

    # loop through days

    for dateStr in dateStrList:

        if (dateStr not in ftpDateList):
            if debug:
                print >>sys.stderr, "WARNING: ignoring date, does not exist on ftp site"
                print >>sys.stderr, "  dateStr: ", dateStr
            continue

        if debug:
            print >>sys.stderr, " dateStr = ", dateStr

        processDate(site, dateStr, tmpDir, targetDir, ftpDateList, ftpFileList)

    # close ftp connection

    inFTP.quit()
                              
########################################################################
# Process a given date

def processDate(site, dateStr, tmpDir, targetDir, ftpDateList, ftpFileList):

    if debug:
        print >>sys.stderr, "Processing site ", site, " for date: ", dateStr
        
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

    # loop through the ftp file list of sounding files,
    # downloading those that have not yet been downloaded

    for idx, ftpFileName in enumerate(ftpFileList, 0):

        if ftpDateList[idx] != dateStr:
            continue

        if debug:
            print >>sys.stderr, " processing ", ftpFileName

        # check file age

        fileTimeStr = ftpFileName[7:9] + '0000'
        fileDateTimeStr = dateStr + fileTimeStr
        localFileName = ftpFileName

        if (int(fileDateTimeStr) < int(startDateTimeStr)):
            if debug:
                print >>sys.stderr, "  file time too old: ", fileDateTimeStr
                print >>sys.stderr, "  startDateTimeStr:  ", startDateTimeStr
            continue

        if (localFileName in localFileList):
            if debug:
                print >>sys.stderr, localFileName," already in localFileList -- ignoring"
            continue

        # process this file

        processFile(localFileName, ftpFileName, tmpDir)

########################################################################
# Process a specific file

def processFile(localFileName, ftpFileName, tmpDir):

    if debug:
        print >>sys.stderr, "Processing file: ", localFileName

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
        return

    file.close()

    if debug:
        print sys.stderr, "  ftped file, stored as ", tmpPath
        
    # Create sounding
    if debug:
        print >>sys.stderr, "  creating skewt plot"

    cmd = 'python -W ignore ' + \
          homeDir + \
          '/python/skewplot_relampago.py --filepath ' + \
          tmpDir + \
          ' --outpath . --format lst'
    runCommand(cmd)

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
    cmd = 'convert ' + soundingPrefix+soundingExt + ' ' + soundingPrefix + '.gif'
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
            runCommand(cmd)
            if debug:
                print >>sys.stderr, "  done ftp'ing skewt plot to ", gifDir

            # Move text file
            cmd = "mv " + tmpPath + " ."
            runCommand(cmd)

    except Exception as e:
        print >>sys.stderr, "FTP failed, exception: ", e

########################################################################
# Run a command in a shell, wait for it to complete

def runCommand(cmd):

    if (debug):
        print >>sys.stderr, "running cmd:",cmd
    
    try:
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print >>sys.stderr, "Child was terminated by signal: ", -retcode
        else:
            if (debug):
                print >>sys.stderr, "Child returned code: ", retcode
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e

########################################################################
# kick off main method

if __name__ == "__main__":

   main()
