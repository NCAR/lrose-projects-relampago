import os
import sys
from ftplib import FTP

ftpServer = 'ftp.eol.ucar.edu'
ftpUser = 'relampago18'
ftpPasswd = 'gr@N!20'
ftpSourceDir = '/sounding/SMN/COR'
destDir = '/tmp/soundings/COR'

# log into NCAR ftp server and look for new soundings
myFTP = FTP(ftpServer)
myFTP.login(ftpUser,ftpPasswd)
myFTP.cwd(ftpSourceDir)
ftpFileList = myFTP.nlst()
print ftpFileList
testFile = ftpFileList[0]

os.chdir(destDir)
tmpPath = testFile
file = open(testFile, 'wb')
myFTP.retrbinary('RETR '+ testFile, file.write)
file.close()
myFTP.quit()
