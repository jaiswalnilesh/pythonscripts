import logging
import sys
import time
import socket
import re
import json
import os
import smtplib
import datetime
from vRADriver.utils.process import die, execute, execute_action
from vRADriver.api.errors import APIError
from vRADriver.api.authapps import APIAuthapp
from vRADriver.utils.filesystem import MultiDimDict
from vRADriver import * #commurl, msgtext
from vRADriver import BASE_DIR, javapath, ccpath

OPERCLIENTS = None

class OPRClient(object):
    """
    A base representation of an cloud tools.
    """
    name = None
    def __init__(self, user_config=None, configs=[], options=None, 
                capabilities=None):
        self.user_config = user_config
        self.configs = configs
        self.options = options
        self.capabilities = capabilities
		# user and pass parameter will be taken from conf file.
        data = {
            "catn" : self.options.catn,
            "oper" : self.options.oper,
            "wflow" : self.options.wflow,
            "vname" : self.options.vname,
			"groupid" : self.options.groupid,
            "cpucnt" : self.options.cpucnt,
            "novm" : self.options.novm,
            "memsize" : self.options.memsize,
            "lease" : self.options.lease,
            "reason" : self.options.reason,
            "rundir" : self.options.rundir,
            "vmid" : self.options.vmid
        }
        self.vmstat = MultiDimDict(2)
        self.gtintval=0
        self.loginonce=1
        logging.debug("Json Data: %s" % data)
        self.data=data
        self.validate_json_data()
       	if self.loginonce: 
            self.api=APIAuthapp(self.data)
            self.loginonce=0

    def validate_json_data(self):
        b=0
        if self.options.job == 'create':
            logging.debug("You opted to create ####")
            for k in self.data.keys():
                if k == 'catn' and self.data[k] == None or \
                   k == 'groupid' and self.data[k] == None or \
                   k == 'rundir' and self.data[k] == None or \
                   k == 'memsize' and self.data[k] == None or \
                   k == 'cpucnt' and self.data[k] == None:
                    b=1
                    break

        if self.options.job == 'poweron' \
              or self.options.job == 'poweroff' or self.options.job == 'delete':
            for k in self.data.keys():
                if k == 'vmid' and self.data[k] == None:
                    print "The key %s value is set to %s" % ( k, self.data[k] )
                    b=1
                    break
       
        if b > 0:
            print "Mandatory parameter %s is missing in data supplied" % ( k )
            sys.exit(1)

    def vcac_vm_request(self):
        """
        Send request to create VM to ucs server and return service request id
        """
        logging.info("Inside vcac_vm_request method base class")
        return None

    def vcac_vm_destroy(self):
        """
        Send request to destroy VM
        """
        logging.info("Inside vcac_vm_destroy")
        return None

    def vcac_worklfow_request(self):
        """
        Send request to create VM to ucs server based on workflow 
        and return service request id
        """
        logging.info("Inside ucsvm_worklfow_request method base class")
        return None

    def vcac_getvm_sr_status(self, serv_req):
        """
        Returns machine name and other data for the service request
        """
        self.reqdata=serv_req
        #Keep requesting the status of the deployment and break when the process is no longer "IN_PROGRESS"
        flag=1
        mailer=0
        s_once=1		
        while flag:
            mailer += 1
            start = time.time()		
            #sleep(10)
            try:
                jfile=self.data['rundir'] + '/' + self.reqdata + '.json'
                vrapath=BASE_DIR + '/' + 'tools/vracc/bin/'
                cmd = "cd %s && ./cloudclient.sh vra request detail --id %s " \
                      "--format JSON --export %s" % \
                         ( vrapath, self.reqdata, jfile )
                logging.info("- vcac cloudclient monitor " \
                             "request id " + self.reqdata + " status")
                request = execute_action(cmd)
            except APIError, e:
                print "Found error## vcac_getvm_sr_status: %s" % str(e)
                sys.exit(1)
				
			# check file exist and not empty
            if os.path.exists(jfile) and os.stat(jfile).st_size > 0:
                with open(jfile) as data_file:
				    requestData = json.load(data_file)
                if requestData['state'] == "SUCCESSFUL":
                    flag=0
                    self.gtintval=mailer
                    tdate=str(datetime.timedelta(seconds=self.gtintval))
                    print "\n"
                    print "SR Reached: %s (HH:MM:SS)\n" % tdate
                    print "SR [ %s ] done, status changed from " \
                                 "IN_PROGRESS to %s\n" % \
                                ( requestData['requestNumber'], requestData['state'])
                    print "\n"
                    break

                    #Work out of the task failed and if not set 
                    #the state variable
                if requestData['state'] == "PROVIDER_FAILED" or \
                         requestData['state'] == "FAILED":
                    state = requestData['state']
                    reason = requestData['requestCompletion']['completionDetails']
                    print "- vcac cloudclient ERROR: %s" % state
                    ops=""
                    self.update_helpdesk(requestData)
                    # Need to add some valuable failed data and do not exit.
                    #sys.exit(" - CLOUDCLIENT ERROR: " + state)
                    return requestData

            end = time.time()
            g=str(datetime.timedelta(seconds=(end - start)))
            parts=g.split(":")
            seconds = int(parts[0])*(60*60) + \
                      int(parts[1])*60 + \
                      float(parts[2])
            time.sleep(60.0)
            mailer = mailer + seconds
            mailer = mailer + 60
            logging.debug('mailer count %s' % mailer)
            if int(mailer) >= 7200 and s_once:
                print "\n"
                print "%s\n" % msgtext
                try:
                    print "Sending notification to IT for ", \
                          "service request: %s\n" % requestData['requestNumber']
                    print "\n"
                    self.ops='gen'
                    self.notify_user(requestData, self.ops)
                    logging.info('Notification send ......')
                except:
                    pass
                s_once=0
                continue
            else:
                logging.info('No need to send notification ......')

        logging.info("- vcac cloudclient request " \
                     "status : %s" % ( requestData['state'] ))
                         
        return requestData
		
    def vcac_getvm_detail_svrreq(self, srid):
        """
        Returns VMs that are currently associated with the 
        specified service request.
        """
        
        self.reqid=srid
        try:
            #Get the name of the vm and return JSON formatted response
            
            jfile=os.path.join("%s", "%s.json") % (self.data['rundir'], self.reqid )
            print "\n"
            print "######## [Waiting for customization for SR: %s] ########" % self.reqid
            print "\n"
            time.sleep(300.0)
            vrapath=BASE_DIR + '/' + 'tools/vracc/bin/'
            cmd="cd %s && ./cloudclient.sh vra machines list --requestId %s --format " \
                "JSON --export %s" % ( vrapath, self.reqid, jfile )
            request = execute_action(cmd)
        except APIError, e:
            print "Found error## vcac_getvm_detail_svrreq: %s" % str(e)
            sys.exit(1)
        else:
            logging.debug("Verify return value after validation query: %s" % (request))
            self.gtintval = self.gtintval + 300
            if os.path.exists(jfile) and os.stat(jfile).st_size > 0:
                logging.info("After provision data file: %s" % (jfile))
                try:
                    with open(jfile) as data_file:
                        reqData = json.load(data_file)
                except APIError, e:
                    print "Loading Json found problem: %s" % str(e)
                    sys.exit(1)

                
                if 'name' in reqData[0] and 'status' in reqData[0]:
                    logging.debug("Value ##### %s" % reqData[0]['name'])
                    for j in range(len(reqData[0]['networks'])):
                        logging.info("Hostname %s configured " \
                                     "with Ip address %s" % \
                                     ( reqData[0]['name'], reqData[0]['networks'][j]['address']))
                        self.vmstat[self.reqid]['vmname']=reqData[0]['name']
                        self.vmstat[self.reqid]['ipaddress']=reqData[0]['networks'][j]['address']
                        self.vmstat[self.reqid]['vmid']=reqData[0]['catalogResource']['parentResourceRef']['id']
                        print "\n"
                        print "SR Reached IP: %s (HH:MM:SS)" % \
                                str(datetime.timedelta(seconds=self.gtintval))
                        break
                else:
                    self.vmstat[self.reqid]['vmname'] = ""
                    self.vmstat[self.reqid]['ipaddress'] = ""
                    self.vmstat[self.reqid]['ipaddress'] = ""

            else:
                logging.warn("- vcac cloudclient json file missing " \
                             "or does not contains hostname or Ip " \
                             "details i.e empty")
                self.vmstat[self.reqid]['vmname'] = ""
                self.vmstat[self.reqid]['ipaddress'] = ""
                self.vmstat[self.reqid]['ipaddress'] = ""
                #self.update_helpdesk(self.reqdata)
                
           
        logging.debug("Before return: %s" % reqData )
        logging.debug("Real Value return: %s" % self.vmstat )
        return self.vmstat
	
    def get_req_data(self, data):
        """ Get status command executed """
        self.rdata=data
        if self.rdata == 1 or \
           self.rdata == 0 or \
           self.rdata == "":
            return 1
        rt=""
        for ot in self.rdata.split('\n'):
            ot = ot.rstrip('\r\n')
            logging.debug(">>>>>>> Check value of output string: %s" % ot)
            if not (ot.startswith("vRA ") or \
                    ot.startswith("JRE Version:") or \
                    ot.startswith("CloudClient is ") or \
                    ot.startswith("true") or \
                    len(ot) == 0):
                if ot.startswith("Error"):
                  print ("Error: %s" % ot.split('Error')[-1])
                  sys.stdout.flush()
                  sys.exit(1)
                else:
                  logging.debug("SR# %s" % ot)
                  rt=ot
                  break
        if not rt:
            print "No service request is found: %s" % rt
            return 1
        else:
            return rt                   
	
    def update_helpdesk(self, data):
        """
        Send notification to helpdesk, they should be creating a urgent ticket.
        """
        self.sr=data
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
        except Exception, imperr:
            print("emailNotify failure - import error %s" % imperr)
            return(-1)
        nHtml = []
        noHtml = ""
        clientEmail = ['helpdesk@mscsoftware.com']
        msg = MIMEMultipart()
        # This is the official email notifier
        rtUser = 'DONOTREPLY@mscsoftware.com'

        msg['From'] = rtUser
        msg['To'] = ", ".join(clientEmail)
        if self.data['groupid'] == 'Nastran-RG':
            msg["Cc"] = "msc-itsupport@mscsoftware.com,\
                         DL-ENG-BUILD@mscsoftware.com,\
                         raj.behera@mscsoftware.com"
        elif self.data['groupid'] == 'Patran-RG':
            msg["Cc"] = "msc-itsupport@mscsoftware.com,\
                         DL-ENG-BUILD@mscsoftware.com,\
                         raj.behera@mscsoftware.com"
        else: 
            msg["Cc"] = "msc-itsupport@mscsoftware.com,\
                         DL-ENG-BUILD@mscsoftware.com,\
                         raj.behera@mscsoftware.com"

        msg['Subject'] = 'Your Request SR# %s for VM provisioning \
                          reported failure for product %s' % \
			            ( self.sr['requestNumber'], pdict[self.data['groupid']] )
        nHtml.append("<html> <head></head> <body> <p>Jenkin's \
                      vCAC cloud client notification<br>")
        nHtml.append("<b>Hi Helpdesk,</b><br><br><br>")
        nHtml.append("Please create a ticket to solve \
                      the following problem and notify infra team.")
        nHtml.append("VM creation readiness from vCAC cloud \
                      is reported failure, \
                      Product is <b>%s</b> is stuck." \
                      % pdict[self.data['groupid']])

        nHtml.append("Regression test for product <b>%s</b> \
                      is impacted.<br><br>" % pdict[self.data['groupid']])
        if os.path.isdir(self.data['rundir']):
            jnfilepath=os.path.join(self.data['rundir'], 'hudjobname.dat')
            if os.path.isfile(jnfilepath):
                lines = [line.rstrip() for line in open(jnfilepath)]
                nHtml.append("Please follow job link for SR# \
                              related information.<br>")
                nHtml.append("Jenkins Effected Job URL: \
                             <a href=%s> Effected Build \
                             Console</a><br><br><br>" % (lines[0]))

        nHtml.append("This needs immediate attention.<br><br>")
        nHtml.append("Regards,<br>")
        nHtml.append("Rtest Administrator.<br>")
        nHtml.append("[Note: This is an automated mail,\
                      Please do not reply to this mail.]<br>")
        nHtml.append("</p> </body></html>")
        noHtml = ''.join(nHtml)
        noBody = MIMEText(noHtml, 'html')
        msg.attach(noBody)
        s = smtplib.SMTP('postgate01.mscsoftware.com')
        s.sendmail(rtUser, [clientEmail] + \
                   msg["Cc"].split(","), msg.as_string())
        s.quit()
        return 0
		
    def get_repository_info(self):
        return None

    def check_options(self):
        pass

    def notify_user(self, svno, ops):
        """
        Send notification to helpdesk, they should 
        be creating a urgent ticket.
        """

        self.sr=svno
        self.ops=ops
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
        except Exception, imperr:
            print("emailNotify failure - import error %s" % imperr)
            return(-1)
        nHtml = []
        noHtml = ""
        clientEmail = ['helpdesk@mscsoftware.com']
        msg = MIMEMultipart()
        # This is the official email notifier
        rtUser = 'DONOTREPLY@mscsoftware.com'

        msg['From'] = rtUser
        msg['To'] = ", ".join(clientEmail)
        if self.data['groupid'] == 'Nastran-RG':
            msg["Cc"] = "msc-itsupport@mscsoftware.com,\
                         DL-ENG-BUILD@mscsoftware.com,\
                         raj.behera@mscsoftware.com"
        elif self.data['groupid'] == 'Patran-RG':
            msg["Cc"] = "msc-itsupport@mscsoftware.com,\
                         DL-ENG-BUILD@mscsoftware.com,\
                         raj.behera@mscsoftware.com"
        else:
            msg["Cc"] = "msc-itsupport@mscsoftware.com,\
                         DL-ENG-BUILD@mscsoftware.com,\
                         raj.behera@mscsoftware.com"

        if self.ops == 'ipnw':
            msg['Subject'] = '%s regression got impacted due \
                              to vCAC cloud for VMID %s' % \
                      ( pdict[self.data['groupid']], self.sr['requestNumber'])
        else:
            msg['Subject'] = '%s regression got impacted due \
                              to vCAC cloud for service request: %s' % \
                      ( pdict[self.data['groupid']], self.sr['requestNumber'])

        nHtml.append("<html> <head></head> <body> <p>Jenkin's \
                     vCAC cloud client notification<br>")
        nHtml.append("<b>Hi Helpdesk,</b><br><br><br>")
        nHtml.append("Please create a ticket to solve the \
                      following problem and notify infra team.")
        if self.ops == 'ipnw':
            nHtml.append("VM creation readiness from vCAC \
                         cloud is taking long time, \
                         vm creation service request completed, \
                         But network configuration is having an issue \
                         for VMID <b>%s</b> is stuck. " % self.sr['requestNumber'])
        else:
            nHtml.append("Creation of VM through vCAC cloud is taking \
                         longer time than expected, the service \
                         request <b>%s</b> is stuck. " % self.sr['requestNumber'])

        nHtml.append("Regression test for product <b>%s</b> \
                      is stuck and impacted.<br><br>" % \
                      pdict[self.data['groupid']])
        if os.path.isdir(self.data['rundir']):
            jnfilepath=os.path.join(self.data['rundir'], 'hudjobname.dat')
            if os.path.isfile(jnfilepath):
                lines = [line.rstrip() for line in open(jnfilepath)]
                nHtml.append("Please follow job link for \
                              SR# related information.<br>")
                nHtml.append("Jenkins Effected Job URL: <a href=%s> \
                             Effected Build Console \
                             </a><br><br><br>" % (lines[0]))

        nHtml.append("This needs immediate attention.<br><br>")
        nHtml.append("Regards,<br>")
        nHtml.append("Rtest Administrator.<br>")
        nHtml.append("[Note: This is an automated mail,\
                     Please do not reply to this mail.]<br>")
        nHtml.append("</p> </body></html>")
        noHtml = ''.join(nHtml)
        noBody = MIMEText(noHtml, 'html')
        msg.attach(noBody)
        s = smtplib.SMTP('postgate01.mscsoftware.com')
        s.sendmail(rtUser, [clientEmail] + msg["Cc"].split(","), msg.as_string())
        s.quit()
        return 0
			
def load_oprclients(options):
    global OPERCLIENTS
    """ keep on adding class for eack capabality support """
    from vRADriver.action.vmcreate import VMCreateClient
    from vRADriver.action.vmdelete import VMDeleteClient
    from vRADriver.action.vmaddisk import VMAddDiskClient
    from vRADriver.action.vmpwron  import VMPowerOnClient
    from vRADriver.action.vmpwroff import VMPowerOffClient

    opr = { 'create' : VMCreateClient(options=options),
	        'delete' : VMDeleteClient(options=options), 
            'poweron' : VMPowerOnClient(options=options), 
            'poweroff' : VMPowerOffClient(options=options), 
            'diskadd' : VMAddDiskClient(options=options), }

    logging.debug("Job option: %s" % (options.job))
    if options.job == None:
        die("one or more mandatory options "
                "are missing, please check usage for more details.")

    logging.debug("Operation name found as : %s" % options.job)
    for key in opr.keys():
        if options.job == key:
            logging.debug("Got instance: %s" % (opr[key]))
            OPERCLIENTS=opr[key]
            break


def scan_usable_client(options):
    from vRADriver.action.vmcreate import VMCreateClient

    repository_info = None
    tool = None

    if OPERCLIENTS is None:
        load_oprclients(options)

    # Try to find the PRD Client we're going to be working with.
    logging.debug('Checking for a %s repository...' % OPERCLIENTS.name)
    repository_info = OPERCLIENTS.get_repository_info()
    if not repository_info:
        logging.debug("ignore the message")

    return (repository_info, OPERCLIENTS)




