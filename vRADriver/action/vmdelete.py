import logging
import os
import re
import stat
import subprocess
import sys
import time

from vRADriver.action import OPRClient
from vRADriver.utils.process import die, execute_action
from vRADriver.utils.filesystem import make_tempfile
from vRADriver.utils.misc import banner
from vRADriver import BASE_DIR, javapath, ccpath

class VMDeleteClient(OPRClient):
    name = 'VMDelete'
    def __init__(self, **kwargs):
        super(VMDeleteClient, self).__init__(**kwargs)
        self.mybuildlog=""
    def get_repository_info(self):
        """ hookup routine for product, not modify this routine """
        return None
    def check_options(self):
        if self.options.job == 'delete' and self.options.vmid == None:
            sys.stderr.write("To perform operation on VM these options"
                            " are mandatory parammeter, one more options"
                            " are missing. \n")
            sys.exit(1)
		#self.options.vdcat
        if self.options.job == 'delete' and self.options.catn \
                or self.options.cpucnt or self.options.groupid \
                or self.options.lease or self.options.memsize \
                or self.options.vname:
            sys.stderr.write("Not supported for this %s operation\n" % self.name)
            sys.exit(1)
                
        if self.options.rundir == None:
            sys.stderr.write("one or more mandatory options"
                             " are missing, please check usage for more details.")
            sys.exit(1)

    def vcac_vm_destroy(self):
        #logging.info("SESSION: %s" % os.environ['CLOUDCLIENT_SESSION_KEY'])
        logging.info("vra user: %s" % os.environ['vra_username'])
        logging.info("JAVA HOME: %s" % os.environ['JAVA_HOME'])
        logging.info("VRA SERVER: %s" % os.environ['vra_server'])
        banner("Start VM Destroy")
        logging.info("Inside vcac_vm_destroy method of client")
        clcdir=os.path.dirname(ccpath)
        #os.environ['CLOUDCLIENT_SESSION_KEY']='hudson-2702123'
        tfile=os.path.join(clcdir, '..', 'CloudClient.properties')
        tcmd="touch " + tfile
        print("\n")
        #sys.stdout.flush()
        if os.path.isfile(tfile):
            print "-vCAC CloudClient properties file does exist"
            os.system(tcmd)
        else:
            print "-vCAC CloudClient properties file does not exist"
        print("\n")
        #sys.stdout.flush()
        vrapath=BASE_DIR + '/' + 'tools/vracc/bin/'
        cmd = "cd %s && ./cloudclient.sh vra login isauthenticated catalog" % ( vrapath )
        self.ret = execute_action(cmd)
        logging.info("Check if user logged in, return's: %s" % self.ret)

        Attempt=1
        step=0
        while Attempt:
            step += 1
            print "Attempt %s to sent destroy request" % step
            cmd = "cd %s && ./cloudclient.sh vra deployment action execute --id %s --action Destroy" % ( vrapath, self.options.vmid )
            logging.info("Destroy CMD: %s" % cmd)
            self.request = execute_action(cmd)
            logging.info("Data recieved: %s" % self.request)
            self.serv_req=self.get_req_data(self.request)
            #logging.info("VM Destroy with status %s" % self.serv_req)
            if self.serv_req == 1:
                logging.info(">>>> Service requested failed trying again")
                print "Delete didnt happened .. trying again"
                time.sleep(90.0)
                continue
            else:
                Attempt=0
                logging.info(">>>> Service requested went through")
                print "Looks like destroy proceeded after attempt %s" % step
                break

        return 0

