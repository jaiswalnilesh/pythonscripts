#!/usr/bin/env python
import os
import getopt
import sys
import glob

try:
    opts, args = getopt.getopt(sys.argv[1:],"r:c:b:e:p:h")
except getopt.GetoptError as err:
	print str(err)
	print("Usage: %s -r /runtime/dir/ -b MARCH2015 -c 12345:12345 -e email -p product" % sys.argv[0])
	sys.exit(2)

rdir=''
cline=''
clist=''
prod=''
for o, a in opts:
	if o == '-r':
		rdir = a
	if o == '-c':
		clist = a
	if o == '-b':
		cline = a
	if o == '-e':
		email = a
	if o == '-p':
		prod = a
	if o == '-h':
		print("Usage: %s -r /runtime/dir/ -b MARCH2015 -c 12345:12345 -e email -p product" % sys.argv[0])
		sys.exit(2)
	
# This function takes two argument
# 1. List of Log path
# 2. List of users to send email with attachment.
def send_email_with_attach(llogs, tolis, msgtext, cline, clist, prod):
	"""
		Send email to selected user with attachment.
	"""
	if len('tolis') == 0:
		return 0
	
	try:
		import smtplib
		from email.MIMEMultipart import MIMEMultipart
		from email.MIMEText import MIMEText
		from email.MIMEBase import MIMEBase
		from email.mime.application import MIMEApplication
		from email import Encoders
		from mimetypes import guess_type
	except:
		pass
		
	bldUser = ''' Build Admin <DONOTREPLY@mscsoftware.com> '''
	replyto="DL-ENG-BUILD@mscsoftware.com"
	toaddr=", ".join(tolis)
	msgsubject = '%s BOM Comparision summary report for codeline %s' % (prod, cline)
		
	msg = MIMEMultipart()


	msg['From'] = bldUser
	msg['Subject'] = msgsubject
	msg['To'] = ", ".join(tolis)
	msg["Cc"] = "nilesh.jaiswal@mscsoftware.com"
	msg["Reply-To"] = replyto

	nHtml = []
	noHtml = ""
	#(cur , prev) = clist.split(':')
	nHtml.append("<html> <head></head> <body> <p>######## Jenkins Build Summary report ########<br><br>")
	nHtml.append("<b>Dear Recipient,</b><br><br><br>")
	nHtml.append("Bom comparison reported attached for current change list %s with previous change list %s<br><br>" % (clist.split(':')[0], clist.split(':')[1]))
	nHtml.append("Regards,<br>")
	nHtml.append("Build Administrator.<br><br>")
	nHtml.append("[Note: This is an automated mail, Please do not reply to this mail.]<br>")
	nHtml.append("</p> </body></html>")
	noHtml = ''.join(nHtml)
	noBody = MIMEText(noHtml, 'html')
	msg.attach(noBody)

	dctype='application/octet-stream'
	for file_path in llogs:
		ctype, encoding = guess_type(file_path)
		if ctype is None or encoding is not None:
			ctype = dctype
		maintype, subtype = ctype.split('/', 1)
				
		try:
			with open(file_path, 'rb') as f:
				part=MIMEBase(maintype,subtype)
				part.set_payload(f.read())
				Encoders.encode_base64(part)
				part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))
				print os.path.basename(file_path)
				msg.attach(part)
		except IOError:
			print "error: Can't open the file %s" % file_path
	
		
	server=smtplib.SMTP('postgate01.mscsoftware.com')
	server.sendmail(msg['From'], tolis + msg["Cc"].split(",") , msg.as_string())
	#print 'Email sent to %s owners' % cline
	server.quit()

if rdir == '':
	print("Usage: %s -r /runtime/dir/ -b MARCH2015 -c 12345:12345 -e email -p product" % sys.argv[0])
	sys.exit(2)

if cline == '':
	print("Usage: %s -r /runtime/dir/ -b MARCH2015 -c 12345:12345 -e email -p product" % sys.argv[0])
	sys.exit(2)
	
if email == '':
	print("Usage: %s -r /runtime/dir/ -b MARCH2015 -c 12345:12345 -e email -p product" % sys.argv[0])
	sys.exit(2)
	
if prod == '':
	print("Usage: %s -r /runtime/dir/ -b MARCH2015 -c 12345:12345 -e email -p product" % sys.argv[0])
	sys.exit(2)
	
if os.path.isfile(email):
	to = [line.strip() for line in open(email, 'r')]
else:
	print ("No mailing list found, using default\n")
	to = ['nilesh.jaiswal@mscsoftware.com']

msgt='BOMCOM'
dirpath = os.path.join(rdir, 'file_*')
files=glob.glob(dirpath)
send_email_with_attach(files, to, msgt, cline, clist, prod)
