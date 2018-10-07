#!/usr/bin/env python

#===========================================================================
#
# Put DOW image data to catalog.
#
#===========================================================================

import os
import sys
from stat import *
import time
import datetime
from datetime import timedelta
import string
import ftplib
import subprocess
from optparse import OptionParser
import xml.etree.ElementTree as ET

def main():

    appName = "put_dow_images_to_catalog.py"

    global options
    global ftpUser
    global ftpPassword
    global ftpDebugLevel

    ftpUser = "anonymous"
    ftpPassword = "front@ucar.edu"

    # parse the command line

    parseArgs()

    # initialize
    
    if (options.debug == True):
        print >>sys.stderr, "======================================================="
        print >>sys.stderr, "BEGIN: " + appName + " " + str(datetime.datetime.now())
        print >>sys.stderr, "======================================================="

    # create tmp dir if necessary
    
    if not os.path.exists(options.temp_dir):
        runCommand("mkdir -p " + options.temp_dir)

    #   compute valid time string

    validTime = time.gmtime(int(options.validTime))
    year = int(validTime[0])
    month = int(validTime[1])
    day = int(validTime[2])
    hour = int(validTime[3])
    minute = int(validTime[4])
    sec = int(validTime[5])
    yyyymmdd = "%.4d%.2d%.2d" % (year, month, day)
    hh = "%.2d" % hour
    mm = "%.2d" % minute
    validDayStr = "%.4d%.2d%.2d" % (year, month, day)
    validTimeStr = "%.4d%.2d%.2d%.2d%.2d" % (year, month, day, hour, minute)
    dateTimeStr = "%.4d%.2d%.2d-%.2d%.2d%.2d" % (year, month, day, hour, minute, sec)

    # compute full path of image
    
    fullFilePath = options.imageDir
    fullFilePath = os.path.join(fullFilePath, options.fileName);
    
    # extract the platform and product from the file name.
    # The image files are named like:
    #   <category>.<legend_label>.<button_label>.<platform>.<time>.png.
    # For example:
    #   radar.DOW6-DBZ.DBZ.DOW6.20150520232246.png (normal)
    #   radar.DOW6-DBZ.DBZ-TRANS.DOW6.20150520232246.png (transparent)

    file_tokens = options.fileName.split(".")
    if (options.debug == True):
        print >>sys.stderr, "filename toks: "
        print >>sys.stderr, file_tokens

    if len(file_tokens) != 6:
        print "*** Invalid file name: ", options.fileName
        sys.exit(0)

    # category

    category = file_tokens[0]
    if (options.category.find("NONE") < 0):
        category = options.category

    # field
        
    field_name = file_tokens[2]
    is_transparent = False
    if (field_name.find("-TRANS") > 0):
        is_transparent = True
    
    # platform name

    platform = file_tokens[3]
    if (options.platform.find("NONE") < 0):
        platform = options.platform
        
    # compute catalog file name

    catalogName = (category + "." + platform + "." +
                   validTimeStr + "." +
                   field_name + "." + "png")

    if (options.debug == True):
        print >>sys.stderr, "catalogName: ", catalogName

    # put the image file

    putFile(fullFilePath, catalogName)

    # create and put the associated KML file, only for transparent images

    if (is_transparent) == True:

        # gis.DOW#.YYYYMMDDHHmm.field_name.kml

        xmlFilePath = os.path.join(options.imageDir, options.fileName[:-3] + "xml")
        kmlCatalogName = "gis." + platform + "." + yyyymmdd + hh + mm + "." + field_name + ".kml"
        kmlFilePath = os.path.join(options.temp_dir, kmlCatalogName)

        if (options.debug == True):
            print >>sys.stderr, "creating kml file: ", kmlFilePath

        createKmlFile(xmlFilePath, kmlFilePath, category, platform, yyyymmdd, hh, mm, field_name)
        putFile(kmlFilePath, kmlCatalogName)

        # Delete the temporary KML file

        cmd = 'rm ' + kmlFilePath
        runCommand(cmd)

    # let the user know we are done

    if (options.debug == True):
        print >>sys.stderr, "======================================================="
        print >>sys.stderr, "END: " + appName + " " + str(datetime.datetime.now())
        print >>sys.stderr, "======================================================="

    sys.exit(0)

########################################################################
# Create the KML file using the information from the XML file generated
# by CIDD.

def createKmlFile(xmlPath, kmlPath, category, platform, yyyymmdd, hh, mm, field_name):

    # Pull the lat/lon limits of the image from the XML file.

    tree = ET.parse(xmlPath)
    lat_lon_box = tree.getroot().find('LatLonBox')
    north = lat_lon_box.find('north').text
    south = lat_lon_box.find('south').text
    west = lat_lon_box.find('west').text
    east = lat_lon_box.find('east').text

    if (options.debug == True):
        print 'north = ', north
        print 'south = ', south
        print 'east = ', east
        print 'west = ', west
    
    # Construct the HREF for this file
    # this is the platform in lower case

    href_platform = platform.lower()
    catalog_name = os.environ['catalog_name']
    
    href = 'http://catalog.eol.ucar.edu/' + catalog_name + '/' \
           + category + '/' + href_platform + '/' \
           + yyyymmdd + '/' + hh + '/' \
           + category + '.' + platform + '.' + yyyymmdd + hh + mm + '.' + field_name + '.png'

    if (options.debug == True):
        print '  href: ', href

    # Create the KML file

    if (options.debug == True):
        print 'Writing KML to file: ', kmlPath

    kml_file = open(kmlPath, 'w')

    kml_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    kml_file.write('<kml xmlns="http://earth.google.com/kml/2.0">\n')
    kml_file.write('  <Document>\n')
    kml_file.write('    <name>' + catalog_name.upper() + ' radar images</name>\n')
    kml_file.write('    <open>1</open>\n')
    kml_file.write('    <Folder>\n')
    kml_file.write('     <name>' + platform + '</name>\n')
    kml_file.write('     <GroundOverlay>\n')
    kml_file.write('        <name>' + platform + '</name>\n')
    kml_file.write('        <Icon>\n')
    kml_file.write('          <href>' + href + '</href>\n')
    kml_file.write('          <refreshMode>onInterval</refreshMode>\n')
    kml_file.write('          <refreshInterval>120</refreshInterval>\n')
    kml_file.write('        </Icon>\n')
    kml_file.write('        <visibility>1</visibility>\n')
    kml_file.write('        <LatLonBox>\n')
    kml_file.write('          <north>' + north + '</north>\n')
    kml_file.write('          <south>' + south + '</south>\n')
    kml_file.write('          <east>' + east + '</east>\n')
    kml_file.write('          <west>' + west + '</west>\n')
    kml_file.write('        </LatLonBox>\n')
    kml_file.write('     </GroundOverlay>\n')
    kml_file.write('     </Folder>\n')
    kml_file.write('  </Document>\n')
    kml_file.write('</kml>\n')

    kml_file.close()

########################################################################
# Put the specified file

def putFile(filePath, catalogName):

    if (options.debug == True):
        print >>sys.stderr, "Handling file: ", filePath
        print >>sys.stderr, "  catalogName: ", catalogName

    # copy the file to the tmp directory

    tmpPath = os.path.join(options.temp_dir, 'ftp.' + catalogName)
    cmd = "cp " + filePath + " " + tmpPath
    runCommand(cmd)

    # send the file to the catalog
    
    ftpFile(catalogName, tmpPath)

    # remove the tmp file
    
    cmd = "/bin/rm " + tmpPath
    runCommand(cmd)
    
    return 0
    
########################################################################
# Ftp the file

def ftpFile(fileName, filePath):

    # set ftp debug level

    if (options.debug == True):
        ftpDebugLevel = 2
    else:
        ftpDebugLevel = 0
    
    targetDir = options.targetDir
    ftpServer = options.ftpServer
    
    # open ftp connection
    
    ftp = ftplib.FTP(ftpServer, ftpUser, ftpPassword)
    ftp.set_debuglevel(ftpDebugLevel)
    
    # go to target dir

    if (options.debug == True):
        print >>sys.stderr, "ftp cwd to: " + targetDir
    
    ftp.cwd(targetDir)

    # put the file

    if (options.debug == True):
        print >>sys.stderr, "putting file: ", filePath

    fp = open(filePath, 'rb')
    ftp.storbinary('STOR ' + fileName, fp)
    
    # close ftp connection
                
    ftp.quit()

    return

########################################################################
# Parse the command line

def parseArgs():
    
    global options

    # parse the command line

    usage = "usage: %prog [options]"
    parser = OptionParser(usage)

    # these options come from the ldata info file

    parser.add_option('--debug',
                      dest='debug', default='False',
                      action="store_true",
                      help='Set debugging on')

    parser.add_option('--verbose',
                      dest='verbose', default='False',
                      action="store_true",
                      help='Set debugging on')

    parser.add_option('--unix_time',
                      dest='validTime',
                      default=0,
                      help='Valid time for image')

    parser.add_option('--full_path',
                      dest='imageDir',
                      default='unknown',
                      help='Full path of image file')

    parser.add_option('--file_name',
                      dest='fileName',
                      default='unknown',
                      help='Name of image file')

    parser.add_option('--rel_file_path',
                      dest='relFilePath',
                      default='unknown',
                      help='Relative path of image file')

    # these options are specific to the image type

    parser.add_option('--ftp_server',
                      dest='ftpServer',
                      default='catalog.eol.ucar.edu',
                      help='Target FTP server')

    catalog_name = os.environ['catalog_name']
    defaultTargetDir = 'pub/incoming/catalog/' + catalog_name
    parser.add_option('--target_dir',
                      dest='targetDir',
                      default='pub/incoming/catalog/dc3',
                      help='Target directory on the FTP server')

    parser.add_option('--category',
                      dest='category',
                      default='NONE',
                      help='Category portion of the catalog file name')

    parser.add_option('--platform',
                      dest='platform',
                      default='NONE',
                      help='Platform portion of the catalog file name.  Overrides platform in image file name if specified.')

    parser.add_option('--href_platform',
                      dest='href_platform',
                      default='',
                      help='The platform name used in the HRFT tag of the KML file.  For this catalog_name, this is the platform name but in all lower case.  Defaults to the the "platform" if not specified. Note that KML files are only generated for transparent images.')

    parser.add_option('--is_transparent',
                      dest='is_transparent', default='False',
                      action="store_true",
                      help='Specifies this is a transparent image.  When specified, "radar_only" is added to the catalog file name and a KML file is generated and copied to the catalog.')

    parser.add_option('--temp_dir',
                      dest='temp_dir',
                      default='/tmp/data/images',
                      help='Temporary directory for creating the KML file to send with the images.')
    parser.add_option('--move_after_copy',
                      dest='moveAfterCopy', default='False',
                      action="store_true",
                      help='Move files to time dir after copy to ftp server')

    parser.add_option('--remove_after_copy',
                      dest='removeAfterCopy', default='False',
                      action="store_true",
                      help='Remove files after copy to ftp server')

    (options, args) = parser.parse_args()

    if (options.verbose):
        options.debug = True

    if (options.debug == True):
        print >>sys.stderr, "Options:"
        print >>sys.stderr, "  debug? ", options.debug
        print >>sys.stderr, "  validTime: ", options.validTime
        print >>sys.stderr, "  imageDir: ", options.imageDir
        print >>sys.stderr, "  relFilePath: ", options.relFilePath
        print >>sys.stderr, "  fileName: ", options.fileName
        print >>sys.stderr, "  ftpServer: ", options.ftpServer
        print >>sys.stderr, "  targetDir: ", options.targetDir
        print >>sys.stderr, "  category: ", options.category
        print >>sys.stderr, "  platform: ", options.platform
        print >>sys.stderr, "  href_platform: ", options.href_platform
        print >>sys.stderr, "  is_transparent: ", options.is_transparent
        print >>sys.stderr, "  temp_dir: ", options.temp_dir
        print >>sys.stderr, "  moveAfterCopy: ", options.moveAfterCopy
        print >>sys.stderr, "  removeAfterCopy: ", options.removeAfterCopy

########################################################################
# Run a command in a shell, wait for it to complete

def runCommand(cmd):

    if (options.debug == True):
        print >>sys.stderr, "running cmd:",cmd
    
    try:
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print >>sys.stderr, "Child was terminated by signal: ", -retcode
        else:
            if (options.debug == True):
                print >>sys.stderr, "Child returned code: ", retcode
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e

########################################################################
# kick off main method

if __name__ == "__main__":

   main()
