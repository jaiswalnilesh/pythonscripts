import logging
import os
import re
import stat
import subprocess
import sys


from vRADriver.action import OPRClient
from vRADriver.utils.process import die, execute#, execute_me
from vRADriver.utils.filesystem import make_tempfile

class VMPowerOffClient(OPRClient):
    name = 'VMPowerOff'
    def __init__(self, **kwargs):
        super(VMPowerOffClient, self).__init__(**kwargs)
        self.mybuildlog=""
    def get_repository_info(self):
        """ hookup routine for product, not modify this routine """
        return None

    def check_options(self):
		
        if self.options.job == 'poweroff' and self.options.vmid == None:
            sys.stderr.write("To perform operation on VM these options"
                            " are mandatory parammeter, one more options"
                            " are missing. \n")
            sys.exit(1)
		#self.options.vdcat
        #if self.options.catn or self.options.vmn or self.options.vdcp\
        #    or self.options.durh or self.options.begt or self.options.qty \
        #    or self.options.mem or self.options.core or self.options.estc \
        #    or self.options.addinfo:
        #    sys.stderr.write("Not supported for this %s operation\n" % self.name)
        #    sys.exit(1)

        if self.options.runtdir == None:
            sys.stderr.write("one or more mandatory options"
                            " are missing, please check usage for more details.")
            sys.exit(1)
