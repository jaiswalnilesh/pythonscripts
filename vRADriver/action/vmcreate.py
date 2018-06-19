import logging
import os
import re
import stat
import subprocess
import sys
import fcntl
import urllib

from vRADriver.action import OPRClient
from vRADriver.utils.process import die, execute_createvm, execute_action
from vRADriver.utils.misc import banner
from vRADriver.utils.filesystem import make_tempfile, MultiDimDict
from vRADriver.api.errors import APIError
from vRADriver import BASE_DIR, javapath, ccpath

class VMCreateClient(OPRClient):
    name = 'VMCreate'
    def __init__(self, **kwargs):
        super(VMCreateClient, self).__init__(**kwargs)
        self.mybuildlog=""
        self.vmdict = MultiDimDict(2)

    def get_repository_info(self):
        """ hookup routine for product, not modify this routine """
        return None

    def check_options(self):
        if self.options.rundir and \
               self.options.groupid and \
               self.options.catn == None:
            sys.stderr.write("one or more mandatory options"
                " are missing, please check usage for more details.")
            sys.exit(1)

    def vcac_vm_request(self):
        """
        Send request to create VM to ucs server and return service request id
        """
        if self.options.lease == None:
            dur="3"
        else:
            dur=self.options.lease
        
        logging.info("vra user: %s" % os.environ['vra_username'])
        logging.info("JAVA HOME: %s" % os.environ['JAVA_HOME'])
        logging.info("VRA SERVER: %s" % os.environ['vra_server'])
        logging.info("Inside vcac_vm_request method of client")
        clcdir=os.path.dirname(ccpath)
        print("\n")
        sys.stdout.flush()
        vrapath=BASE_DIR + '/' + 'tools/vracc/bin/'
        cmd = "cd %s && ./cloudclient.sh vra login isauthenticated catalog" % ( vrapath )
        self.ret = execute_action(cmd)
        logging.info("Check if user logged in, return's: %s" % self.ret)
        Attempt=1
        step=0
        while Attempt:
            step += 1
            mymsg=self.options.catn + '|' + self.options.groupid
            print "Attempt %s to sent request" % step
            cmd = "cd %s && ./cloudclient.sh vra catalog request submit --id  %s --groupid %s --reason \"%s\" --leasedays  %s --cpu  %s --memory  %s" % ( vrapath, self.options.catn, self.options.groupid, mymsg, dur, self.options.cpucnt, self.options.memsize )
            logging.info("CMD Generation: %s" % cmd)
            self.request = execute_createvm(cmd) 
            logging.info("Data recieved: %s" % self.request)
            # fetch the service request number , success etc from data supplied
            self.serv_req=self.get_req_data(self.request)			
            print("\n")
            if self.serv_req == 1:
                print "No SR# found ... Trying again\n"
                logging.info(">>>> Service requested failed, trying again")
                continue
            else:
                Attempt=0
                logging.info(">>>> Service requested went through")
                print "Looks like creation is started after attempt %s" % step
                break
        # return status of VM creation i.e SUCCESSFULL or Error
        self.ret=self.vcac_getvm_sr_status(self.serv_req)
        if self.ret['state'] == "PROVIDER_FAILED" or \
                    self.ret['state'] == "FAILED":
            print "- vcac cloudclient ERROR: " \
                         "VM Creation for SR# %s " \
                         "reported %s" % ( self.ret['requestNumber'], self.ret['state'] )
            print "VM Request id: %s" % self.serv_req
            print("\n")
            #return 1
            sys.exit(1)
        print("\n")
        if self.options.switch:
            vmreadyfilepath=os.path.join("%s", "reserved_mcs.dat") % \
                            self.data['rundir']
        else:
            vmreadyfilepath=os.path.join("%s", "rerun_reserved_mcs.dat") % \
                            self.data['rundir']

        logging.debug('File name is: %s' % vmreadyfilepath)
        sys.stdout.flush()
        flag=1
        s=0
        import time
        while flag:
            s += 1
            time.sleep(30.0)
            print ("Check for VM details using vra machines list --requestId: %s" % s)
            self.vcac_getvm_detail_svrreq(self.serv_req)
            if not self.vmstat[self.serv_req]['vmname'] or \
                    not self.vmstat[self.serv_req]['ipaddress'] or \
                    not self.vmstat[self.serv_req]['vmid']:
                continue
            else:
                flag=0
                print ("All details available in attempt: %s" % s)
                break
        sys.stdout.flush()
        print("\n")
        logging.debug("VM details: %s" % self.vmstat)
        for i in self.vmstat.keys():
            if self.vmstat[i].has_key('vmid'):
                print("VMID: %s" % self.vmstat[i]['vmid'])
                vmid=self.vmstat[i]['vmid']
                if self.vmstat[i].has_key('vmname'):
                    print("VMNAME: %s" % self.vmstat[i]['vmname'])
                    vmname=self.vmstat[i]['vmname']
                if self.vmstat[i].has_key('ipaddress'):
                    print("IPADD: %s" % self.vmstat[i]['ipaddress'])
                    ipaddress=self.vmstat[i]['ipaddress']
                print("\n")
				# perform file write operation
				# some time hostname field is empty, ehnce using second filed as instanceid
                try:
                    with open( vmreadyfilepath, 'a' ) as f:
                        fcntl.flock(f, fcntl.LOCK_EX)
                        f.write("%s\t %s\t %s\t %s\n" % \
                            ( vmid, vmname, ipaddress, vmname ) )
                        fcntl.flock(f, fcntl.LOCK_UN)
                except IOError, e:
                    print "Found error: %s" % str(e)
                    sys.exit(1)
                else:
                    return 0

