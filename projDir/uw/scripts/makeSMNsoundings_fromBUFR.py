#!/usr/bin/python

import os
import sys
import glob
#from shutil import copyfile
from ftplib import FTP
import time
import datetime
from datetime import timedelta
import subprocess

debug = 0
ftpServer = '181.30.169.202'
ftpUser = 'relopsftp'
ftpPasswd = 'rayos2018'
sourceDir = '/upload/sounding/SMN'
targetDir = '/home/storm/relops/soundings/SMN_bufr'
processedDir = targetDir+'/processed'
tmpDir = '/tmp/SMN/'
gifDir = targetDir+'/gifs'
sites = ['COR','MDZ','SIS','VMRS']
ftpCatalogServer = 'catalog.eol.ucar.edu'
ftpCatalogUser = 'anonymous'
catalogDestDir = '/pub/incoming/catalog/relampago'

# check to make sure tmpDir exists
if not os.path.exists(tmpDir):
    os.makedirs(tmpDir)

# log into NCAR ftp server and get ftpFileList
myFTP = FTP(ftpServer)
myFTP.set_debuglevel = 2   # verbose
myFTP.login(ftpUser,ftpPasswd)
myFTP.cwd(sourceDir)
tmpFtpList = myFTP.nlst()
ftpFileList = []
for ftpFile in tmpFtpList:
    if ftpFile.startswith('radiosondeos'):
        ftpFileList.append(ftpFile)
if debug:
    print >>sys.stderr, "ftpFileList = ", ftpFileList
        
# go to local directory and get localFileList
localDir = processedDir
if not os.path.exists(localDir):
    os.makedirs(localDir)
os.chdir(localDir)
if debug:
    print >>sys.stderr, "  localDir = ", localDir
tmpFileList = os.listdir('.')
localFileList = []
for localFile in tmpFileList:
    if localFile.startswith('radiosondeos'):
        localFileList.append(localFile)
if debug:
    print >>sys.stderr, "  localFileList: ", localFileList

# compare lists and find new files on ftp site
newFileList = list(set(ftpFileList) - set(localFileList))
if debug:
    print >>sys.stderr, "  newFileList: ", newFileList
    
# download the new files to targetDir
for ftpFile in newFileList:
    if debug:
        print >>sys.stderr, "  ftpFile: ", ftpFile
    tmpPath = os.path.join(targetDir, ftpFile)
    file = open(tmpPath, 'w')
    myFTP.retrbinary('RETR '+ ftpFile, file.write)
    file.close()
    if debug:
        print sys.stderr, "  ftped file to: ", tmpPath

# convert new BUFR files to ascii format
cmd = 'python -W ignore /home/storm/brodzik/python/relampago/parse_bufr.py '+targetDir+' '+tmpDir
if debug:
    print sys.stderr, "   cmd = ", cmd
os.system(cmd)
if debug:
    print sys.stderr, "Done converting BUFR files to ascii format"

for i in range(0,len(sites)):
    if debug:
        print >>sys.stderr, "Processing ",sites[i]," Data"
    sourceDir = tmpDir+sites[i]
    if debug:
        print >>sys.stderr, "   sourceDir = ", sourceDir
    if os.path.exists(sourceDir):
        if debug:
            print >>sys.stderr, "   sourceDir exists"
        os.chdir(sourceDir)
        flist = os.listdir('.')
        for file in flist:
            if debug:
                print >>sys.stderr, "   file = ", file
            # create skewt
            fileFullPath = sourceDir+'/'+file
            cmd = 'python -W ignore /home/storm/brodzik/python/brody/skewplot_relampago.py --file '+fileFullPath+' --outpath '+sourceDir+' --format lst'
            if debug:
                print sys.stderr, "   cmd = ", cmd
            os.system(cmd)
            # move ascii file to final location
            finalDir = targetDir+'/'+sites[i]
            if not os.path.exists(finalDir):
                os.makedirs(finalDir)
            cmd = 'mv '+sourceDir+'/'+file+' '+finalDir+'/'+file
            if debug:
                print sys.stderr, "   cmd = ", cmd
            os.system(cmd)
            # convert png to gif skewt move to gifsDir
            for skewtFile in glob.glob(sourceDir+'/upperair*.png'):
                if debug:
                    print sys.stderr, "   skewtFile = ", skewtFile
                (skewtPrefix,skewtExt) = os.path.splitext(skewtFile)
                cmd = 'convert '+skewtPrefix+skewtExt+' '+skewtPrefix+'.gif'
                if debug:
                    print sys.stderr, "   cmd = ", cmd      
                os.system(cmd)
                cmd = 'rm '+skewtFile
                if debug:
                    print sys.stderr, "   cmd = ", cmd      
                os.system(cmd)
                skewtFullPath = skewtPrefix+'.gif'
                
                # ftp skewt to catalog site
                if debug:
                    print >>sys.stderr, "  ftp'ing skewt plot to catalog"
                catalogFTP = FTP(ftpCatalogServer,ftpCatalogUser)
                catalogFTP.cwd(catalogDestDir)
                skewtFile = os.path.basename(skewtFullPath)
                if debug:
                    print >>sys.stderr, "  skewtFile = ", skewtFile
                #file = open(skewtFullPath,'rb')
                #catalogFTP.storbinary('STOR '+skewtFile,file)
                #file.close()
                catalogFTP.quit()
                if debug:
                    print >>sys.stderr, "  done ftp'ing skewt plot to catalog"
                    
                # Move skewt file
                cmd = "mv " + skewtFullPath + ' ' + gifDir
                if debug:
                    print sys.stderr, "   cmd = ", cmd      
                os.system(cmd)
                        
# close ftp connection
myFTP.quit()
    
