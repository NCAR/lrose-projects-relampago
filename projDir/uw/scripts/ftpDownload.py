#!/usr/bin/python

import os
import sys
from ftplib import FTP

ftpServer = 'ftp.eol.ucar.edu'
ftpUser = 'relampago18'
ftpPasswd = 'gr@N!20'
tmpDir = '/home/storm/relops/soundings/SMN/tmp'
sourceDir = 'sounding/SMN/COR'
targetDir = '/home/storm/relops/soundings/SMN/COR'

fileToDownload = '181101_12_87344.lst'

myFTP = FTP(ftpServer)
myFTP.login(ftpUser,ftpPasswd)
myFTP.cwd(sourceDir)
ftpFileList = myFTP.nlst()

tmpPath = os.path.join(tmpDir, fileToDownload)
file = open(tmpPath,'wb')
myFTP.retrbinary('RETR '+ fileToDownload, file.write)

myFTP.quit()
