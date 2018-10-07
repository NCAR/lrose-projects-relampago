#!/usr/bin/env python

# utility to check that h2odial transferred data

from datetime import datetime, timedelta
import os,os.path
import smtplib
import sys
import time
global receivers

#receivers = [ "spuler@ucar.edu", "7207712435@txt.att.net", 
#"bruce@ucar.edu", "3038340147@vtext.com",
#"mhayman@ucar.edu", "7203001017@txt.att.net",
#"stillwel@ucar.edu", "72032917@txt.att.net"]

#receivers = [ "spuler@ucar.edu", "7207712435@txt.att.net", "stillwel@ucar.edu", "7203293917@txt.att.net"]
receivers = [ "stillwel@ucar.edu"]

def check_file(dir, now=datetime.utcnow()):
    """ check if a data file exists with the correct name"""
    # compute the time one hour ago
    #prev = now - timedelta(hours=1)
    
    #fname = now.strftime('%Y/%y%m%dFF/%H/Online_Raw_Data.dat')
    fname = now.strftime('%Y/%Y%m%d/MCSsample%H0000.nc')
    fullname = os.path.join(dir, fname)
    exists = os.path.exists(fullname)
    delta = timedelta(minutes = 99)
    if exists:
	delta =  now - datetime.fromtimestamp(os.path.getctime(fullname))

     
    return (exists, fullname, delta)

def mail_warning(sender, receivers, msg):
    try:
	smtp = smtplib.SMTP('localhost')
	print 'sending ', msg
	smtp.sendmail(sender, receivers, msg)
    except smtplib.SMTPException:
	print "Error: unable to send email"

 


if __name__ == '__main__':
# DIAL01
   # exists, file, delta = check_file('/export/eldora1/h2o_data/')
   # exists, file, delta = check_file('/export/eldora1/wvdial_1_data/')
# DIAL02
   # exists, file, delta = check_file('/export/eldora1/MSU_h2o_data/') 
    exists, file, delta = check_file('/export/eldora1/wvdial_2_data/')

    max_delta = timedelta(minutes=9)
    sender = "rsfdata@eldora.eol.ucar.edu"

    missing_msg = """From: {0}
To: {1}
Subject: missing h2o data 

{2} not found
"""
    stale_msg = """From: {0}
To: {1}
Subject: stale h2o data 

{2} has not been updated for {3}
"""
    if exists:
	if delta < max_delta:
	    print('file {0} exists (and is up-to-date) '.format(file) )
	else:
	    print('file {0} is stale '.format(file))
	    hours, remainder = divmod(delta.total_seconds(), 3600)
	    minutes, seconds = divmod(remainder, 60)
	    dstr = "%02d:%02d:%02d" % (hours, minutes, seconds)
	    mail_warning(sender, receivers, 
		stale_msg.format(sender,",".join(receivers), file, dstr))
	
    else:
	print('file {0} is missing '.format(file))
	
	mail_warning(sender, receivers, 
		missing_msg.format(sender, ",".join(receivers), file) )
	
