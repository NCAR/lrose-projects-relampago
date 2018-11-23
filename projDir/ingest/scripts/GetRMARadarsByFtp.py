#!/usr/bin/env python

#=====================================================================
#
# Download RMA radar files from ftp site
#
#=====================================================================

import os
import sys
import time
import datetime
from datetime import timedelta
import string
import ftplib
import subprocess
from optparse import OptionParser

def main():

    global options
    global ftpUser
    global ftpPassword
    global ftpDebugLevel
    global tmpDir
    global startTime, endTime

    global thisScriptName
    thisScriptName = os.path.basename(__file__)

    # parse the command line

    parseArgs()

    # initialize
    
    beginString = "BEGIN: " + thisScriptName
    today = datetime.datetime.now()
    beginString += " at " + str(today)
    
    if (options.force):
        beginString += " (ftp forced)"

    print "\n========================================================"
    print beginString
    print "========================================================="

    # create tmp dir if necessary

    try:
        os.makedirs(options.tmpDir)
    except OSError as exc:
        if (options.verbose):
            print >>sys.stderr, "WARNING: cannot make tmp dir: ", options.tmpDir
            print >>sys.stderr, "  ", exc
            
    # set ftp debug level

    if (options.verbose):
        ftpDebugLevel = 2
    elif (options.debug):
        ftpDebugLevel = 1
    else:
        ftpDebugLevel = 0
    
    # get current date and time

    nowTime = time.gmtime()
    now = datetime.datetime(nowTime.tm_year, nowTime.tm_mon, nowTime.tm_mday,
                            nowTime.tm_hour, nowTime.tm_min, nowTime.tm_sec)
    nowDateStr = now.strftime("%Y%m%d")
    nowDateTimeStr = now.strftime("%Y%m%d%H%M%S")

    # compute time strings

    startDateTimeStr = startTime.strftime("%Y%m%d%H%M%S")
    startDateStr = startTime.strftime("%Y%m%d")
    endDateTimeStr = endTime.strftime("%Y%m%d%H%M%S")
    endDateStr = endTime.strftime("%Y%m%d")

    # set up list of days to be checked

    nSecs = endTime - startTime
    if (options.debug):
        print >>sys.stderr, "  nSecs: ", nSecs

    sys.exit(0)

    nDays = (pastSecs / 86400) + 1
    dateStrList = []
    for iDay in range(0, nDays):
        deltaSecs = timedelta(0, iDay * 86400)
        dayTime = now - deltaSecs
        dateStr = dayTime.strftime("%Y%m%d")
        dateStrList.append(dateStr)

    # debug print

    if (options.debug):
        print >>sys.stderr, "  time now: ", nowDateTimeStr
        print >>sys.stderr, "  getting data after: ", startDateTimeStr
        print >>sys.stderr, "  nDays: ", nDays
        print >>sys.stderr, "  dateStrList: ", dateStrList

    if (options.skipFtp):
        print "skipping FTP of", options.sourceDir, " to", options.targetDir
        sys.exit(0)

    # open ftp connection
    
    ftp = ftplib.FTP(options.ftpServer, options.ftpUser, options.ftpPasswd)
    ftp.set_debuglevel(ftpDebugLevel)

    # got to radar directory on the ftp site

    ftp.cwd(options.sourceDir)
    ftpDateList = ftp.nlst()

    # loop through days

    count = 0
    for dateStr in dateStrList:

        if (dateStr not in ftpDateList):
            if (options.verbose):
                print >>sys.stderr, "WARNING: ignoring date, does not exist on ftp site"
                print >>sys.stderr, "  dateStr: ", dateStr
            continue

        # make the target directory

        localDayDir = os.path.join(options.targetDir, dateStr)
        try:
            os.makedirs(localDayDir)
        except OSError as exc:
            if (options.verbose):
                print >>sys.stderr, "WARNING: trying to create dir: ", localDayDir
                print >>sys.stderr, "  ", exc
        os.chdir(localDayDir)

        # get local file list - i.e. those which have already been downloaded

        localFileList = os.listdir('.')
        localFileList.reverse()
        if (options.verbose):
            print >>sys.stderr, "  localFileList: ", localFileList
            
        # get ftp server file list, for day dir
        
        ftpDayDir = os.path.join(options.sourceDir, dateStr)
        ftp.cwd(ftpDayDir)
        ftpFileList = ftp.nlst()
        ftpFileList.reverse()
        if (options.verbose):
            print >>sys.stderr, "  ftpFileList: ", ftpFileList

        # loop through the ftp file list, downloading those that have
        # not yet been downloaded

        for ftpFileName in ftpFileList:
            fileTimeStr = ftpFileName[0:6]
            fileDateTimeStr = dateStr + fileTimeStr
            localFileName = dateStr + '_' + ftpFileName
            if (int(fileDateTimeStr) < int(startDateTimeStr)):
                if (options.verbose):
                    print >>sys.stderr, "  file time too old: ", fileDateTimeStr
                    print >>sys.stderr, "  startDateTimeStr:  ", startDateTimeStr
            else:
                if (localFileName not in localFileList):
                    downloadFile(ftp, dateStr, ftpFileName)
                    count = count + 1
                    
    # close ftp connection
    
    ftp.quit()

    if (count == 0):
        print "---->> No files to download"
        
    print "==============================================================="
    print "END: " + thisScriptName + str(datetime.datetime.now())
    print "==============================================================="

    sys.exit(0)

########################################################################
# Download a file into the current directory

def downloadFile(ftp, dateStr, fileName):
    
    if (options.debug):
        print >>sys.stderr, "  downloading file: ", fileName
        
    # get file, store in tmp

    localFileName = dateStr + '_' + fileName
    tmpPath = os.path.join(options.tmpDir, localFileName)

    if (options.verbose):
        print >>sys.stderr, "retrieving file, storing as tmpPath: ", tmpPath
    ftp.retrbinary('RETR '+ fileName, open(tmpPath, 'wb').write)

    # move to final location - i.e. this directory
    
    cmd = "mv " + tmpPath + " ."
    runCommand(cmd)

    # write latest_data_info
    
    fileTimeStr = fileName[0:6]
    fileDateTimeStr = dateStr + fileTimeStr
    
    relPath = os.path.join(dateStr, localFileName)
    cmd = "LdataWriter -dir " + options.targetDir \
          + " -rpath " + relPath \
          + " -ltime " + fileDateTimeStr \
          + " -writer " + thisScriptName \
          + " -dtype mdv"
    runCommand(cmd)

########################################################################
# Parse the command line

def parseArgs():
    
    global options
    global startTime, endTime

    # parse the command line

    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option('--debug',
                      dest='debug', default=False,
                      action="store_true",
                      help='Set debugging on')
    parser.add_option('--verbose',
                      dest='verbose', default=False,
                      action="store_true",
                      help='Set verbose debugging on')
    parser.add_option('--force',
                      dest='force', default=False,
                      action="store_true",
                      help='Force ftp transfer')
    parser.add_option('--ftpServer',
                      dest='ftpServer',
                      default='200.16.116.24',
                      help='Name of ftp server host')
    parser.add_option('--ftpUser',
                      dest='ftpUser',
                      default='Lvidal',
                      help='User for ftp host')
    parser.add_option('--ftpPasswd',
                      dest='ftpPasswd',
                      default='lv1d4l',
                      help='Passwd for ftp host')
    parser.add_option('--sourceDir',
                      dest='sourceDir',
                      default='/L2/RMA1',
                      help='Path of source directory')
    parser.add_option('--targetDir',
                      dest='targetDir',
                      default='/home/relamp/projDir/data/relampago/raw/radar/catchup/RMA1',
                      help='Path of target directory')
    parser.add_option('--tmpDir',
                      dest='tmpDir',
                      default='/tmp/radar/RMA1',
                      help='Path of tmp directory')
    parser.add_option('--start',
                      dest='startTime',
                      default='2018 11 01 00 00 00',
                      help='Start time for retrieval')
    parser.add_option('--end',
                      dest='endTime',
                      default='2018 11 10 00 00 00',
                      help='End time for retrieval')

    (options, args) = parser.parse_args()

    if (options.verbose):
        options.debug = True

    year, month, day, hour, minute, sec = options.startTime.split()
    startTime = datetime.datetime(int(year), int(month), int(day),
                                  int(hour), int(minute), int(sec))

    year, month, day, hour, minute, sec = options.endTime.split()
    endTime = datetime.datetime(int(year), int(month), int(day),
                                int(hour), int(minute), int(sec))

    if (options.debug):
        print >>sys.stderr, "Options:"
        print >>sys.stderr, "  debug? ", options.debug
        print >>sys.stderr, "  force? ", options.force
        print >>sys.stderr, "  ftpServer: ", options.ftpServer
        print >>sys.stderr, "  ftpUser: ", options.ftpUser
        print >>sys.stderr, "  sourceDir: ", options.sourceDir
        print >>sys.stderr, "  targetDir: ", options.targetDir
        print >>sys.stderr, "  tmpDir: ", options.tmpDir
        print >>sys.stderr, "  startTime: ", startTime
        print >>sys.stderr, "  endTime: ", endTime

########################################################################
# Run a command in a shell, wait for it to complete

def runCommand(cmd):

    if (options.debug):
        print >>sys.stderr, "running cmd:",cmd
    
    try:
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print >>sys.stderr, "Child was terminated by signal: ", -retcode
        else:
            if (options.debug):
                print >>sys.stderr, "Child returned code: ", retcode
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e

########################################################################
# kick off main method

if __name__ == "__main__":

   main()
