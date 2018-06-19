#
# __init__.py -- Basic version and package information
#
# Copyright (c) 2014  Nilesh Jaiswal
#

# The version of vRADriver
#
# This is in the format of:
#
#   (Major, Minor, Micro, alpha/beta/rc/final, Release Number, Released)
#
import os
VERSION = (1, 2, 1, 'final', 0, True)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
javapath=r'/usr/java/jre1.8.0_91'
ccli=r'cloudclient.sh'
ccpath=BASE_DIR + '/' + 'tools/vracc/bin/' + ccli
itdata=os.path.join(BASE_DIR, 'data', 'local', 'itInventory.txt')
pdict={}
if os.path.exists(itdata):
    with open(itdata, 'r') as book_file:
        for l in book_file:
            #print l
            if len(l) > 0 and l.strip():
                if not l.startswith("#"):
                    l = l.rstrip('\r\n')
                    pdict[l.split(':')[0]]=l.split(':')[1]
else:
    # Default setting
    pdict = {'Nastran-RG': 'Nastran', 
             'Patran-RG': 'Patran', 
             'Adams-RG': 'Adams', 
             'Apex-RG': 'Apex', 
             'MSComp-RG': 'MSComp', 
             'SimM-RG': 'Simmanager',
             'Marc-RG': 'Marc',
             'Mentat-RG': 'Mentat',
             'DRA-RG': 'Harmony', 
             'Harmony-RG': 'Harmony', 
             'SimX-RG': 'SimX',
             'SimD-RG': 'SimD',
             'Dytran-RG': 'Dytran',
             'Easy5-RG': 'Easy5',
             'ABLD': 'DynamicBuild'}

msgtext = '''
    Dear User,

    It's looks like VM creation time is too long, This issue is
    reported to IT helpdesk for support,
    service request will be created and assign to IT team shortly.

    Cloud service request for VM creation is having an issue.

    Thank you for your patience.

    -Rtest Adminitrator
    '''
		
def get_version_string():
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += ".%s" % VERSION[2]

    if VERSION[3] != 'final':
        if VERSION[3] == 'rc':
            version += ' RC%s' % VERSION[4]
        else:
            version += ' %s %s' % (VERSION[3], VERSION[4])

    if not is_release():
        version += " (dev)"

    return version


def get_package_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += ".%s" % VERSION[2]

    if VERSION[3] != 'final':
        version += '%s%s' % (VERSION[3], VERSION[4])

    return version


def is_release():
    return VERSION[5]


__version_info__ = VERSION[:-1]
__version__ = get_package_version()

