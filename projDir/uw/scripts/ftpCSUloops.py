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
debug = 1
secsPerDay = 86400
pastSecs = 108000
ncarServer = '192.168.1.40'
ncarUser = 'relamp'
ncarPasswd = 'relamp18!!'
ncarSourceDirBase = '/data/relamp/data.server/relampago/cfradial/CSU_CHIVO/radar_data/figures'
targetDirBase = '/home/storm/relops/radar/CSU_CHIVO'
tmpDir = '/tmp/CSU_CHIVO_RHI'
tmpDirHold = tmpDir+'/hold'
image = 'rhi_true_aspect'
prodName_raw = 'rhi_sweep'
prodName = 'rhi_sector_6vars_loop'
ftpCatalogServer = 'catalog.eol.ucar.edu'
ftpCatalogUser = 'anonymous'
catalogDestDir = '/pub/incoming/catalog/relampago'

# check for tmpDir, tmpDirHold, localLoopDir
if not os.path.exists(tmpDir):
    os.makedirs(tmpDir)
if not os.path.exists(tmpDirHold):
    os.makedirs(tmpDirHold)
localLoopDir = targetDirBase+'/rhi_sector_loops'
if not os.path.exists(localLoopDir):
    os.makedirs(localLoopDir)

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

    # make the localDayDir and localLoopDir
    localDayDir = os.path.join(targetDir, dateStr)
    if not os.path.exists(localDayDir):
        os.makedirs(localDayDir)
    localLoopDayDir = os.path.join(localLoopDir, dateStr)
    if not os.path.exists(localLoopDayDir):
        os.makedirs(localLoopDayDir)

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
        if prodName_raw in tmpFile:
            ftpFileList.append(tmpFile)
    #remove last volume or partial volume from list - we'll get them next time
    ftpFileList.sort()
    sweep = 99
    while sweepNum != 0:
        ftpFileList.remove(ftpFileList[-1])
        tmpFile = ftpFileList[-1]
        (prefix,ext) = os.path.splitext(tmpFile)
        (date,time,junk,sweep) = prefix.split('_')
        sweepNum = int(sweep[5:])
    ftpFileList.remove(ftpFileList[-1])
    #ftpFileList.reverse()
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
                    print >>sys.stderr, "    localFileName = ", localFileName, " NOT in localFileList"
                ftpFileNameFull = ftpDayDir+'/'+ftpFileName
                localFileNameFull = localDayDir+'/'+ftpFileName
                ftp.get(ftpFileNameFull,localFileNameFull)
                if debug:
                    print sys.stderr, "    ftped file to ", localDayDir
                #copy/rename file to tmpDir
                (ftpFileNamePrefix,ftpFileNameExt) = os.path.splitext(ftpFileName)
                (datePlus,time,junk1,junk2) = ftpFileNamePrefix.split('_')
                date = datePlus[3:]
                sweepNum = junk2[5:]
                if len(sweepNum) < 2:
                    sweepNum = '0'+sweepNum
                junk2 = 'sweep_'+sweepNum
                newFileName = date+'_'+time+'_'+junk2+ftpFileNameExt
                newFileNameFull = tmpDir+'/'+newFileName
                cmd = 'cp '+localFileNameFull+' '+newFileNameFull
                if debug:
                    print >>sys.stderr, "    cmd = ", cmd
                os.system(cmd)
            else:
                if debug:
                    print >>sys.stderr, "    localFileName = ", localFileName, " in localFileList"

    #sys.exit()
                    
    #either move file to save location or process sector
    lastSweepNum = '99'
    firstFile = 1
    tmpFileList = os.listdir(tmpDir)
    tmpFileList.sort()
    for idx in range(0,len(tmpFileList)):
        tmpFile = tmpFileList[idx]
        if tmpFile.endswith('png'):
            if debug:
                print >>sys.stderr, "tmpDir  = ", tmpDir
                print >>sys.stderr, "tmpFile = ", tmpFile
            tmpFileFull = tmpDir+'/'+tmpFile
            (tmpFilePrefix,tmpFileSuffix) = os.path.splitext(tmpFile)
            if debug:
                print >>sys.stderr, "   tmpFilePrefix = ", tmpFilePrefix
                print >>sys.stderr, "   tmpFileSuffix = ", tmpFileSuffix
            (date,time,junk,sweepNum) = tmpFilePrefix.split('_')
            if debug:
                print >>sys.stderr, "    lastSweepNum = ", lastSweepNum, " and sweepNum = ", sweepNum
            if firstFile:
                cmd = 'mv '+tmpFileFull+' '+tmpDirHold
                if debug:
                    print >>sys.stderr, "    sweepNum > lastSweepNum - continue"
                    print >>sys.stderr, "    cmd = ", cmd
                os.system(cmd)
                lastSweepNum = sweepNum
                firstFile = 0
            elif (sweepNum > lastSweepNum) and (idx < len(tmpFileList)-1):
                cmd = 'mv '+tmpFileFull+' '+tmpDirHold
                if debug:
                    print >>sys.stderr, "    sweepNum > lastSweepNum - continue"
                    print >>sys.stderr, "    cmd = ", cmd
                os.system(cmd)
                lastSweepNum = sweepNum
            else:
                # make animated gif from files in tmpDirHold
                loopFile = 'radar.CSU_CHIVO.'+date+time+'.'+prodName+'.gif'
                loopFileFull = tmpDirHold+'/'+loopFile
                cmd = 'convert -delay 20 -loop 0 '+tmpDirHold+'/*.png '+loopFileFull
                if debug:
                    print >>sys.stderr, "    cmd = ", cmd
                os.system(cmd)
                    
                # copy animated gif to local dir
                cmd = '/bin/cp '+loopFileFull+' '+localLoopDayDir
                if debug:
                    print >>sys.stderr, "    cmd = ", cmd
                os.system(cmd)
                    
                # ftp animated gif to catalog
                #catalogFTP = FTP(ftpCatalogServer,ftpCatalogUser)
                #catalogFTP.cwd(catalogDestDir)
                if debug:
                    print >>sys.stderr, "    ftp'ing loopFileFull = ", loopFileFull
                #file = open(loopFileFull,'rb')
                #catalogFTP.storbinary('STOR '+loopFile,file)
                #file.close()
                #catalogFTP.quit()
                    
                # remove all files in tmpDirHold
                cmd = '/bin/rm '+tmpDirHold+'/*'
                if debug:
                    print >>sys.stderr, "    cmd = ", cmd
                os.system(cmd)
                    
                # move new file to tmpDirHold
                cmd = 'mv '+tmpFileFull+' '+tmpDirHold
                if debug:
                    print >>sys.stderr, "    cmd = ", cmd
                os.system(cmd)
                lastSweepNum = sweepNum

# close sftp connection
ftp.close()
ssh.close()
    






    

                              
