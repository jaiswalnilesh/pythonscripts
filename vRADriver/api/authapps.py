import os
import platform
import re
import sys
import logging
import json
import fcntl
import commands
import ConfigParser
import logging
import uuid
import subprocess
from vRADriver.api.errors import APIError
from vRADriver import *
from vRADriver.utils.process import die, execute_createvm

# set home path
if 'HOME' in os.environ:
    homepath = os.environ["HOME"]
elif 'USERPROFILE' in os.environ:
    homepath = os.environ["USERPROFILE"]
else:
    homepath = ''

config = ConfigParser.ConfigParser()
subname = os.path.join(BASE_DIR, 'lib', 'conf')
logging.debug("subname: %s" % subname)
configfile=os.path.join(subname, 'conf.cfg')
if os.path.exists(configfile):
    config.readfp(open(configfile))
else:
    print "vRADriver failed to found conf.cfg file. please contact admin for resolution."
    sys.exit(1)
	

try:
    # Specifically import json_loads, to work around some issues with
    # installations containing incompatible modules named "json".
    from json import loads as json_loads
except ImportError:
    from simplejson import loads as json_loads
	
class APIAuthapp(object):
	
	#def __init__(self, data, cookie_file, rsp=None, *args, **kwargs):
    def __init__(self, data):
		#logging.debug("This from APIAuthapp: %s" % self.data)
        if config.has_option('svrparam', 'vcacsvr'):
            self.url = config.get('svrparam','vcacsvr')
            logging.info("Found Automation center URL  %s" % self.url)
        else:
            print "vRADriver util failed to find svrparam configuration option ucssvr"
            sys.exit(1)

        self.data=data
        self.qlogin=self.get_username() 
        self.sesid=self.qlogin + '-' + str(uuid.uuid4()).split('-')[-1]
        # Do not delete these env
        os.environ['CLOUDCLIENT_SESSION_KEY']='madson'
        logging.debug("cloudclient session key: %s" % os.environ['CLOUDCLIENT_SESSION_KEY'])
        os.environ['vra_server']=self.url
        os.environ['vra_username']="%s@<FQDN>" % self.qlogin
        os.environ['vra_password']='########'
        #self.qpasswd=self.get_credentials()
        
        logging.info("Found username: %s" % self.qlogin)
        logging.info("Data: %s" % self.data)
        os.environ['JAVA_HOME']=javapath

    def get_username(self):
        """
           Return user based on product
        """
        logging.debug("VDC NAME: %s" % self.data['groupid'])
        uvdc={}
        username=""
        user_vdcmap = os.path.join(BASE_DIR, 'data', 'local', 'user-vdcmap.txt')
        if os.path.exists(user_vdcmap):
            with open(user_vdcmap) as fp:
                for line in fp.readlines():
                    if not line.startswith("#"):
                        (key, value)=line.split('=')
                        logging.debug("VALUE: %s" % value)
                        logging.debug("KEY: %s" % key)
                        uvdc[key]=value.rstrip('\r\n')
            for i in uvdc.keys():
                logging.debug("fetch value: %s" % i)
                if i == '000':
                    username=uvdc[i]
                    break
        else:
            print "Cloud user vdc mapping file not present: %s" % user_vdcmap
        
        logging.debug("Username found in user-vdcmap.txt: %s" % username)
		#print "Username found in user-vdcmap.txt: %s" % username
        if username == "":
            username='hudson'
            logging.debug("Resetting username to default: %s" % username)

        return username

    def get_credentials(self):
        """
            Return credential
        """
        clipath = os.path.join(BASE_DIR, 'tools', 'credStore')
        logging.debug("path of cli binary: %s" % clipath)
        cmdcli="%s -d decrypt -s 'Hardworking' -k NOUSE_1234567" % clipath
        logging.debug("Command: %s" % cmdcli)
        cred=execute_createvm(cmdcli)
        logging.debug("PWD: %s" % cred)
        return cred

def debug1(s):
    #if options and options.debug:
    print ">>> %s" % s
