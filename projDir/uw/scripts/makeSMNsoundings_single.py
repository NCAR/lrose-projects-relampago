#!/usr/bin/python

import os
import sys
from ftplib import FTP

# Check input parameters
if len(sys.argv) != 2:
    print >>sys.stderr, "Useage: ",sys.argv[0]," [sndgTextFile]"
    quit()
sndgTextFile = sys.argv[1]

# Parse filename for info
(sndgPrefix,sndgExt) = os.path.splitext(sndgTextFile)
(date,hour,siteNum) = sndgPrefix.split('_')
dateStr = '20'+date
timeStr = hour+'0000'
if siteNum == '87344':
    siteName = 'COR'
    longSiteName = 'Cordoba_AR'
elif siteNum == '87418':
    siteName = 'MDZ'
    longSiteName = 'Mendoza_AR'
elif siteNum == '87244':
    siteName = 'VMRS'
    longSiteName = 'Villa_Maria_AR'

# User inputs
debug = 1
baseDir = '/home/storm/relops/soundings/SMN'
targetDir = baseDir+'/'+siteName
gifDir = baseDir+'/gifs'
ftpCatalogServer = 'catalog.eol.ucar.edu'
ftpCatalogUser = 'anonymous'
catalogDestDir = '/pub/incoming/catalog/relampago'

# make day directory
localDayDir = os.path.join(targetDir, dateStr)
if not os.path.exists(localDayDir):
    os.makedirs(localDayDir)
if debug:
    print >>sys.stderr, "  localDayDir = ", localDayDir

# Create sounding
if debug:
    print >>sys.stderr, "  creating skewt plot"
cmd = 'python -W ignore /home/storm/brodzik/python/brody/skewplot_relampago.py --filepath . --outpath . --format '+sndgExt
if debug:
    print >>sys.stderr, " cmd = ",cmd                        
os.system(cmd)
    
included_extensions = ['jpg', 'bmp', 'png', 'gif']
imageFiles = [fn for fn in os.listdir('.')
              if any(fn.endswith('png') for ext in included_extensions)]
if len(imageFiles) != 0:
    skewtFile = imageFiles[0]
else:
    print >>sys.stderr, "  skewt not created . . . exiting"
    quit()
if debug:
    print >>sys.stderr, "  Done creating skewt = ", skewtFile

# Convert png to gif and remove old png file
(skewtPrefix,skewtExt) = os.path.splitext(skewtFile)
cmd = 'convert '+skewtPrefix+skewtExt+' '+skewtPrefix+'.gif'
os.system(cmd)
cmd = 'rm '+skewtFile
os.system(cmd)
skewtFile = skewtPrefix+'.gif'
if debug:
    print >>sys.stderr, " Done converting png to gif ", skewtFile

# Move text file
cmd = 'mv '+skewtFile+' '+localDayDir
os.system(cmd)

# Ftp skewt to catalog
if debug:
    print >>sys.stderr, "  ftp'ing skewt plot to catalog"
catalogFTP = FTP(ftpCatalogServer,ftpCatalogUser)
catalogFTP.cwd(catalogDestDir)
#skewtPath = os.path.join(localDayDir,skewtFile)
skewtPath = os.path.join(_______,skewtFile)
if debug:
    print >>sys.stderr, "  skewtPath = ", skewtPath
file = open(skewtPath,'rb')
catalogFTP.storbinary('STOR '+skewtFile,file)
file.close()
catalogFTP.quit()
if debug:
    print >>sys.stderr, "  done ftp'ing skewt plot to catalog"
                    
# Move skewt file
cmd = "mv " + soundingFile + ' ' + gifDir
os.system(cmd)
if debug:
    print >>sys.stderr, "  done ftp'ing skewt plot to ", gifDir
