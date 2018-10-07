#!/usr/bin/env python

# ========================================================================== #
#
# rsync H20 DIAL data from field to this server
#
# ========================================================================== #

import os
import sys
from optparse import OptionParser
import time
import datetime
from datetime import date
from datetime import timedelta
import subprocess
from subprocess import PIPE

def main():

    global options
    global driveList
    global deviceTable
    global nowSecs
    global driveIndex

    # parse the command line

    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option('--debug',
                      dest='debug',
                      default='False',
                      action="store_true",
                      help='Set debugging on')
    parser.add_option('--verbose',
                      dest='verbose',
                      default='False',
                      action="store_true",
                      help='Set verbose debugging on')
    parser.add_option('--targetDir',
                      dest='targetDir',
                      default='/export/eldora1/h2o_data',
                      help='Path of source directory')
    parser.add_option('--rsyncSource',
                      dest='rsyncSource',
                      default='rsync://166.164.215.174/wvdial/',
                      #default='rsync://128.117.47.87/wvdial/',
                      help='Source address for dial, from which to grab data')
    parser.add_option('--ndaysLookback',
                      dest='ndaysLookback',
                      default=7,
                      help='Number of days to look back for data')
    
    (options, args) = parser.parse_args()

    if (options.verbose == True):
        options.debug = True

    if (options.debug == True):
        print >>sys.stderr, "Running: ", os.path.basename(__file__)
        print >>sys.stderr, "  Options:"
        print >>sys.stderr, "    Debug: ", options.debug
        print >>sys.stderr, "    Verbose: ", options.verbose
        print >>sys.stderr, "    targetDir: ", options.targetDir
        print >>sys.stderr, "    rsyncSource: ", options.rsyncSource
        print >>sys.stderr, "    ndaysLookback: ", options.ndaysLookback

    # get current time

    now = time.gmtime()
    nowTime = datetime.datetime(now.tm_year, now.tm_mon, now.tm_mday,
                                now.tm_hour, now.tm_min, now.tm_sec)

    # do rsync for last ndaysLookback days

    idays = range(options.ndaysLookback)

    for iday in idays:
        dtime = timedelta(iday)
        dayTime = nowTime - dtime
        doRsyncForDay(dayTime, iday)
        
    sys.exit(0)

########################################################################
# Perform rsync for a specified day

def doRsyncForDay(dayTime, iday):

    yearStr = str(dayTime.year)
    yrStr = yearStr[-2:]

    sourceDirRoot = yrStr + ('%.2d%.2d' % (dayTime.month, dayTime.day))

    if (options.debug == True):
        print >>sys.stderr, "======================="
        print >>sys.stderr, "Performing rsync for day: "
        print >>sys.stderr, "    dayTime: ", dayTime
        print >>sys.stderr, "    yearStr: ", yearStr
        print >>sys.stderr, "    yrStr: ", yrStr
        print >>sys.stderr, "    sourceDirRoot: ", sourceDirRoot

    # make target dir as required
    
    targetDayDir = os.path.join(options.targetDir, yearStr)
    if (os.path.isdir(targetDayDir) != True):
        # make target dir since it does not already exist
        if (options.debug == True):
            print >>sys.stderr, "  making target day dir: ", targetDayDir
        os.makedirs(targetDayDir)

    # go to target dir
    
    os.chdir(targetDayDir)

    if (options.debug == True):
        print >>sys.stderr, "  Changed to dir: ", targetDayDir
        print >>sys.stderr, "  CWD: ", os.getcwd()
        
    # create rsync command

    if (iday == 0):
        cmd = 'rsync -av "' + options.rsyncSource + sourceDirRoot + '*" .'
    else:
        cmd = 'rsync -av "' + options.rsyncSource + sourceDirRoot + '*" .'

    # run the command
    
    runCommand(cmd)

    return

########################################################################
# Run a command in a shell, wait for it to complete

def runCommand(cmd):

    if (options.debug == True):
        print >>sys.stderr, "running cmd:",cmd
    
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
	stdoutData, stderrData = p.communicate()
	print >>sys.stderr, "stdout = ", stdoutData
	print >>sys.stderr, "stderr = ", stderrData
        if p.returncode < 0:
            print >>sys.stderr, "Child was terminated by signal: ", -p.returncode
        else:
            if (options.debug == True):
                print >>sys.stderr, "Child returned code: ", p.returncode
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e

########################################################################
# Run - entry point

if __name__ == "__main__":
   main()

