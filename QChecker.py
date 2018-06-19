#!/usr/bin/python
__author__ = 'njaiswal'
import sys, os
import sys
from datetime import datetime
from optparse import OptionParser
import logging
from logging import handlers
import inspect
import ConfigParser
import subprocess
from collections import defaultdict
import time
import signal
import sys
import json
from Queue import Queue
from heapq import heappush, heappop

''' Global defination '''
options = None
configs = []

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if sys.platform.startswith('linux'):
  quelog=os.path.join(BASE_DIR, 'lib', 'logs', 'QueueLog.log')
else:
  quelog='//<networkpath>' + os.path.join(BASE_DIR, 'lib', 'logs', 'QueueLog.log')
print ("quelog: %s" % quelog)
breqapath=r'/<path/of/data/repository>'
qacld='Quality/cloud'
javapath=r'/usr/java/jre1.8.0_91'
#resumeid=""
config = ConfigParser.ConfigParser()
configfile = os.path.join(BASE_DIR, 'lib', 'conf', 'conf.cfg')
if os.path.exists(configfile):
  config.readfp(open(configfile))
else:
  print "Failed to found conf.cfg file. please contact admin for resolution."
  sys.exit(1)

''' End of defination '''

class MultiDimDict(dict):
  def __init__(self, dimensions):
    dict.__init__(self)
    self.dimension = dimensions - 1
  def __getitem__(self, key):
    if self.dimension == 0:
      return dict.__getitem__(self, key)
    else:
      return self.setdefault(key, MultiDimDict(self.dimension))
  def __setitem__(self, key, value):
    if self.dimension == 0:
      dict.__setitem__(self, key, value)
    else:
      raise "Illegal assignment to non-leaf dimension!"

class PriorityQueue(Queue):
  # Initialize the queue representation
  def _init(self, maxsize):
    self.maxsize = maxsize
    self.queue = []

  # Put a new item in the queue
  def _put(self, item):
    return heappush(self.queue, item)

  # Get an item from the queue
  def _get(self):
    return heappop(self.queue)
	
class APIAuthapp(object):
  def __init__(self):
    if config.has_option('svrparam', 'vcacsvr'):
      self.url = config.get('svrparam','vcacsvr')
      logger.info("Found Automation center URL "+ self.url)
    else:
      logger.warn("Failed to find svrparam configuration option vcacsvr")
      sys.exit(1)
    self.qlogin=self.get_username() 
    # Do not delete these env
    os.environ['CLOUDCLIENT_SESSION_KEY']='%s' % self.get_username()
    logger.debug("cloudclient session key: "+ os.environ['CLOUDCLIENT_SESSION_KEY'])
    os.environ['vra_server']=self.url
    os.environ['vra_username']="%s@<FQDN>" % self.get_username()
    os.environ['vra_password']=str(self.get_credentials())
   
    logger.info("Found username: "+ self.qlogin)
    os.environ['JAVA_HOME']=javapath

  def get_clonecnt(self):
    ''' Read conf and return clone count '''
    if config.has_option('clonecontrol', 'clcnt'):
      self.ccnt = config.get('clonecontrol','clcnt')
      logger.info("Total Clone upper limit "+ self.ccnt)
    else:
      logger.warn("Failed to find clonecontrol configuration option clcnt")
      sys.exit(1)
    return self.ccnt

  @staticmethod
  def get_status_check():
    ''' Read conf and return state want to check '''
    if config.has_option('status', 'what'):
      state = config.get('status','what')
      logger.info("Status to check in vRA "+ state)
    else:
      logger.warn("Failed to find status configuration option what")
      sys.exit(1)
    ''' This should return IN_PROGRESS '''
    return state
	
  def get_username(self):
    ''' Return user based on product '''
    uvdc={}
    username=""
    user_vdcmap = os.path.join(BASE_DIR, 'data', 'local', 'user-vdcmap.txt')
    if os.path.exists(user_vdcmap):
      with open(user_vdcmap) as fp:
        for line in fp.readlines():
          if not line.startswith("#"):
            (key, value)=line.split('=')
            logger.debug("VALUE: "+ value)
            logger.debug("KEY: "+ key)
            uvdc[key]=value.rstrip('\r\n')
        for i in uvdc.keys():
          logger.debug("fetch value: "+ i)
          if i == '000':
            username=uvdc[i]
            break
    else:
      logger.info("Cloud user vdc mapping file not present: "+user_vdcmap)
    
    logger.debug("Username found in user-vdcmap.txt: %s" % username)
    if username == "":
      username='hudson'
      logger.debug("Resetting username to default: %s" % username)
    
    return username
  
  def get_credentials(self):
    ''' Return credential '''
    clipath = os.path.join(BASE_DIR, 'tools', 'credStore')
    if not os.path.exists(clipath):
      logger.warn("Non existence filepath "+ clipath)
      if not options.debug:
        sys.exit(1)
    logger.debug("path of cli binary: %s" % clipath)
    cmdcli="%s -d decrypt -s 'Hardworker' -k NOUSE_1234567" % clipath
    #logger.debug("Command: %s" % cmdcli)
    cred=execute_createvm(cmdcli)
    #logger.debug("PWD: %s" % cred)
    return cred
  
  @staticmethod	
  def get_vratatus(state=None):
    ''' Returns state from vcac server '''
    tstat_cnt=0
    try:
      import tempfile
      tf = tempfile.NamedTemporaryFile()
      jfile = tf.name + '.json'
      sys.stdout.flush()
      vrapath=BASE_DIR + '/' + 'tools/vracc/bin/'
      #cmd = "cd %s && ./cloudclient.sh vra login isauthenticated catalog" % ( vrapath )
      #ret = execute_action(cmd)
      cmd = "cd %s && ./cloudclient.sh vra request list --state %s  --pageSize 25 " \
                "--format JSON --export %s" % \
               ( vrapath, state, jfile )
      logging.debug("Executing check for status from vRA")
      request = execute_action(cmd)
    except ValueError, e:
      logger.warn("Found error## get_vratatus: %s"+ str(e))
      sys.exit(1)
    else:
      # check file exist and not empty
      if os.path.exists(jfile) and os.stat(jfile).st_size > 0:
        try:
          with open(jfile) as data_file:
            reqdata = json.load(data_file)
        except ValueError, e:
          logging.warn("Loading json found problem: %s" % str(e))
          sys.exit(1)
        if len(reqdata) > 0:
          for i in range(len(reqdata)):
            if reqdata[i]['state'] == state:
              tstat_cnt += 1

    return tstat_cnt

def get_jenkins_url():
  ''' Read conf and return state want to check '''
  if config.has_option('jenkins', 'server'):
    jurl = config.get('jenkins','server')
    logger.info("Jenkins URL :" + jurl)
  else:
    logger.warn("Failed to find status configuration option what")
    sys.exit(1)
    ''' This should return JENKINS URL '''
  return jurl

def execute_createvm(cmd):
  ''' Executing cloudclient which handles output with different way '''
  logger.debug("Executing command from execute_createvm")
  r = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  status=r.wait()
  p = r.communicate()
  if status != 0:
    logger.debug("value status: %d" % (status))
    #logger.debug("value p[0]: %s" % (p[0]))
    #logger.debug("value p[0]: %s" % (p[1]))
    logger.debug("value p[1]: %s" % (len(p[1])))
    logger.debug("value p[0]: %s" % (len(p[0])))
    #logger.debug("Error: %s" % p[0].split('Error')[-1])
    sys.stdout.flush()
    if status == 1:
      if len(p[1]) > 0:
        return p[1]
      elif len(p[0]) > 0:
        return p[0]
      else:
        return status
  logger.debug('Return value in execute_createvm: %s' % p[0])
  return p[0]

def execute_action(cmd):
  ''' Executing cloudclient which handles output with different way - Another method '''
  
  logger.debug("Inside executeRequst: %s" % cmd)
  r = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  status=r.wait()
  p = r.communicate()
  if status != 0:
    logger.debug("value status: %d" % (status))
    logger.debug("value p[1]: %s" % (p[1]))
    logger.debug("value p[0]: %s" % (p[0]))
    return p[1]
  logger.debug("Return value in execute_action: %s" % p[0])
  return p[0]
    
def parse_options(args):

  usage = "usage: %prog [options] arg"
  parser = OptionParser(usage)
  global logger

  parser.add_option("-s", "--state",
                    dest="state",
                    default=get_config_value(configs, 'STATE', False),
                    help="Mandatory: Enter State of request you want to check in cloud")
  parser.add_option("-j", "--job",
                    dest="job",
                    default=get_config_value(configs, 'JOB', False),
                    help="Optional: Setting priority to the job")
  parser.add_option("-p", "--product",
                    dest="product",
                    default=get_config_value(configs, 'PRODUCT', False),
                    help="Mandatory: Enter product")
  parser.add_option("-b", "--cline",
                    dest="cline",
                    default=get_config_value(configs, 'CLINE', False),
                    help="Mandatory: Enter Codeline or Branch name")
  parser.add_option("-a", "--arch",
                    dest="arch",
                    default=get_config_value(configs, 'ARCH', False),
                    help="Mandatory: Enter OS type")
  parser.add_option("-q", "--maxmcs",
                    dest="maxmcs",
                    default=get_config_value(configs, 'MAXMCS', False),
                    help="Maximum machines you want to use for QC run Eg: 2 or 4 or 6")
  parser.add_option("-n", "--clist",
                    dest="clist",
                    default=get_config_value(configs, 'CLIST', False),
                    help="Mandatory: Enter perforce changelist number")
  parser.add_option("-r", "--rtest",
                    dest="rtest",
                    default=get_config_value(configs, 'RTEST', False),
                    help="Enter regeression test type")
  parser.add_option("-l", "--changeconfig",
                    dest="changeconfig",
                    default=get_config_value(configs, 'CHANGECONFIG', False),
                    help="Rtest Change config parameters, use it carefully")
  parser.add_option("-y", "--qaupd",
                    action="store_true", dest="qaupd",
                    default=get_config_value(configs, 'QAUPD', False),
                    help="Sync QA area")
  parser.add_option("-e", "--edition",
                    dest="edition",
                    default=get_config_value(configs, 'EDITION', False),
                    help="Variable choice what you want to run, it can be mmbom,SE,REG, ....")
  parser.add_option("-w", "--rerun",
                    action="store_true", dest="rerun",
                    default=get_config_value(configs, 'RERUN', False),
                    help="Perform rerun")
  parser.add_option("-x", "--qaper",
                    dest="qaper",
                    default=get_config_value(configs, 'QAPER', False),
                    help="Rtest Percentage check limit")
  parser.add_option("-f", "--flavor",
                    dest="flavor",
                    default=get_config_value(configs, 'FLAVOR', False),
                    help="CDE version c16, c17, c18 etc")
  parser.add_option("-i", "--iprior",
                    dest="iprior",
                    default=get_config_value(configs, 'IPRIOR', False),
                    help="Priority of job 'GEN for General', 'CRI for Critical'")					
  parser.add_option("-d", "--debug",
                    action="store_true", dest="debug",
                    default=get_config_value(configs, 'DEBUG', False),
                    help="display debug output")

  (globals()["options"], args) = parser.parse_args(args)

  function_name = inspect.stack()[1][3]
  logger = logging.getLogger(function_name)
  #logger.setLevel(logging.DEBUG) #By default, logs all messages

  if options.debug:
    #fh = logging.FileHandler(quelog)
    logger.setLevel(logging.DEBUG)
    fh = handlers.RotatingFileHandler(quelog, maxBytes=10485760, backupCount=10, encoding="UTF-8")
    fh.setLevel(logging.DEBUG)
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    fh.doRollover()
    logger.addHandler(fh)

  return args

def read_queue_data (quefile):
  ''' Read queue table and return '''
  logger.debug("Entering read_queue_data")
  logger.debug("Queue table chart: "+ quefile)
  
  list=[]
  quedict=MultiDimDict(2)
  with open(quefile, 'r') as f:
    for line in f:
      if line.startswith('#') or not line.strip():
        continue
      else:
        list.append(line.rstrip('\n'))

  for idx in list:
    #print idx.split()[0]
    if len(idx.split()) == 8:
      quedict[idx.split()[0]]['PRODUCT']=idx.split()[1]
      quedict[idx.split()[0]]['CLINE']=idx.split()[2]
      quedict[idx.split()[0]]['TIMESTAMP']=idx.split()[3]
      quedict[idx.split()[0]]['JOBID']=idx.split()[4]
      quedict[idx.split()[0]]['ARCH']=idx.split()[5]
      quedict[idx.split()[0]]['STATUS']=idx.split()[6]
      quedict[idx.split()[0]]['PQUE']=idx.split()[7]
    if len(idx.split()) == 0:
      quedict[idx.split()[0]]['PRODUCT']=""
      quedict[idx.split()[0]]['CLINE']=""
      quedict[idx.split()[0]]['TIMESTAMP']=""
      quedict[idx.split()[0]]['JOBID']=""
      quedict[idx.split()[0]]['ARCH']=""
      quedict[idx.split()[0]]['STATUS']=""
      quedict[idx.split()[0]]['PQUE']=""
  #print "Show quetable entries"+ quedict
  logger.debug("Exiting read_queue_data")
  logger.debug("Found dictionary length: %s" % len(quedict))
  return quedict

def appendjob_quetable(quedict, jobid, quefile, pque):
  ''' Priority can be assign based on 'GEN for General', 'CRI for Critical' '''
  logger.debug("Entering appendjob_quetable")
  logger.debug("Queue table chart: "+ quefile)
  
  timef=datetime.now().strftime("%Y-%m-%d-%H:%M")
  dsize=len(quedict)
  logger.info("Current queue status: %s" % dsize)
  if dsize == 0:
    qid=1;
  else:
    newsize=len(quedict)
    qid=newsize + 1
    logger.debug("New Que entry: %d" % qid)
  logger.info("Queue id : %d" % qid)
  quedict[str(qid)]['PRODUCT']=options.product
  quedict[str(qid)]['CLINE']=options.cline
  quedict[str(qid)]['TIMESTAMP']=timef
  quedict[str(qid)]['JOBID']=jobid
  quedict[str(qid)]['ARCH']=options.arch
  quedict[str(qid)]['STATUS']='Queued'
  quedict[str(qid)]['PQUE']=pque
  
  logger.debug("Updating queue table data")
  logger.debug("File name: "+quefile)
  print("As per current queue status, Your job id %s will be processed %d in the Queue" % (jobid, qid))
  with open(quefile, "w") as myfile:
    for key in sorted([int(x) for x in quedict.keys()]):
      if 'PRODUCT' in quedict[str(key)] and 'CLINE' in quedict[str(key)] and \
          'TIMESTAMP' in quedict[str(key)] and 'JOBID' in quedict[str(key)] and \
          'ARCH' in quedict[str(key)] and 'STATUS' in quedict[str(key)] and 'PQUE' in quedict[str(key)]:
        val="%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % \
            (key, quedict[str(key)]['PRODUCT'], \
             quedict[str(key)]['CLINE'], quedict[str(key)]['TIMESTAMP'], \
             quedict[str(key)]['JOBID'], quedict[str(key)]['ARCH'], \
             quedict[str(key)]['STATUS'], quedict[str(key)]['PQUE'])
        myfile.write(val)
  
  logger.debug("Exiting appendjob_quetable")
  return 0

def enquejobs(jobid, quefile, pque):
  logger.debug("Entering enquejobs")
  logger.debug("Queue table chart: "+ quefile)
  quedict=MultiDimDict(2)
  quefile_lockfile = os.path.basename(quefile) + '.lock'
  quefile_lockfpath = os.path.join(BASE_DIR, 'globalqdir', quefile_lockfile)
  logger.debug("Check existence of quefile lock path")
  if os.path.exists(quefile_lockfpath):
    lock=1
    while lock:
      logger.debug("Sleeping for 2 minutes since found lock")
      time.sleep(2.0)
      if not os.path.exists(quefile_lockfpath):
        lock=0

  cmd='/usr/bin/lockfile -10 ' + quefile_lockfpath
  os.system(cmd)
  if os.path.exists(quefile):
    logger.debug("Reading quefile data")
    quedict=read_queue_data(quefile)
    logger.debug("Reading quefile done")
  
  for qid in sorted([int(x) for x in quedict.keys()]):
    if quedict[str(qid)]['JOBID'] == str(jobid):
      logger.debug("Quedict data jobid matches with supplied jobid :"+ str(jobid))
      os.unlink(quefile_lockfpath) 
      return 0
  logger.debug("Length of quedict %d" % len(quedict)) 
  appendjob_quetable(quedict, jobid, quefile, pque)
  os.unlink(quefile_lockfpath)
  logger.debug("Exiting enquejobs")
  return 0

def dequeue_table(quefile):
  logger.debug("Entering dequeue_table")
  logger.debug("Queue table chart: "+ quefile)
  
  dequedict=MultiDimDict(2)
  quefile_lockfile = os.path.basename(quefile) + '.lock'
  quefile_lockfpath = os.path.join(BASE_DIR, 'globalqdir', quefile_lockfile)
  
  if os.path.exists(quefile_lockfpath):
    lock=1
    while lock:
      time.sleep(2.0)
      if not os.path.exists(quefile_lockfpath):
        lock=0
  cmd='/usr/bin/lockfile -10 ' + quefile_lockfpath
  os.system(cmd)
  if os.path.exists(quefile):
    dequedict=read_queue_data(quefile)

  hsize=len(dequedict)
  if hsize == 0:
    os.unlink(quefile_lockfpath)
    return 0
  logger.debug("Queue table entries: %s" % dequedict)
  q = PriorityQueue()
  for qid in sorted([int(x) for x in dequedict.keys()]):
    if dequedict[str(qid)]['PQUE'] == 'CRI':
      # initialise the priority based on CRI factor, CRI is 0
      king=0
      q.put((king,str(qid)))
    else:
      # General category
      q.put((qid, str(qid)))

  global resumeid
  if not q.empty():
    uqid=q.get()[1]
    if dequedict[str(uqid)]['PQUE'] == 'CRI':
      print ("\n")
      print("Your job got express token, moving ahead in queue, now you will be serve asap .....")
      resumeid=dequedict[str(uqid)]['JOBID']
    elif dequedict[str(uqid)]['PQUE'] == 'GEN' and int(uqid) == 1:
      logger.info("You are generic user")
      resumeid=dequedict[str(uqid)]['JOBID']
    del dequedict[str(uqid)]
  print ("\n")  
  print("Currently Processing job id: "+ resumeid)
	
  # for qid in sorted([int(x) for x in dequedict.keys()]):
    # if qid == 1:
      # resumeid=dequedict[str(qid)]['JOBID']
      # del dequedict[str(qid)]
  logger.debug("You updated deuedict %s" % dequedict) 
  hsize=len(dequedict)
  if hsize == 0:
    f=open(quefile, 'r')
    val=len(f.readlines())
    f.close()
    if val == 1:
      f=open(quefile, 'w')
      f.write("")
      f.close()
    os.unlink(quefile_lockfpath)
    return 0

  # re-indexing the hash
  temph={}
  num=0
  for key in sorted([int(x) for x in dequedict.keys()]):
    num += 1
    try:
      temph[str(num)]=dequedict[str(key)]
    except:
      raise

  dequedict={}
  logger.debug("Reindexed dictionary %s" % temph)
  dequedict=temph
  
 
  # updating table after dequeue step and reindexing
  with open(quefile, "w") as myfile:
    for key in sorted([int(x) for x in dequedict.keys()]):
      if 'PRODUCT' in dequedict[str(key)] and 'CLINE' in dequedict[str(key)] and \
          'TIMESTAMP' in dequedict[str(key)] and 'JOBID' in dequedict[str(key)] and \
          'ARCH' in dequedict[str(key)] and 'STATUS' in dequedict[str(key)] and 'PQUE' in dequedict[str(key)]:
        val="%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % \
            (key, dequedict[str(key)]['PRODUCT'], \
             dequedict[str(key)]['CLINE'], dequedict[str(key)]['TIMESTAMP'], \
             dequedict[str(key)]['JOBID'], dequedict[str(key)]['ARCH'], \
             dequedict[str(key)]['STATUS'], dequedict[str(key)]['PQUE'])
        myfile.write(val)
		

  os.unlink(quefile_lockfpath)
  if os.path.exists(quefile_lockfpath):
    cmd='rm -f ' + quefile_lockfpath
    os.system(cmd)

  logger.debug("Exiting dequeue_table")
  return 0

def dequetable_at_abort ():
  logger.debug("Entering dequetable_at_abort")
  logger.debug("Queue table chart: "+ quefile)
  dequedict=MultiDimDict(2)
  quefile_lockfile = os.path.basename(quefile) + '.lock'
  quefile_lockfpath = os.path.join(BASE_DIR, 'globalqdir', quefile_lockfile)
  
  if os.path.exists(quefile_lockfpath):
    lock=1
    while lock:
      time.sleep(2.0)
      if not os.path.exists(quefile_lockfpath):
        lock=0
  cmd='/usr/bin/lockfile -10 ' + quefile_lockfpath
  os.system(cmd)
  if os.path.exists(quefile):
    dequedict=read_queue_data(quefile)

  hsize=len(dequedict)
  if hsize == 0:
    os.unlink(quefile_lockfpath)
    return 0

  for qid in sorted([int(x) for x in dequedict.keys()]):
    if dequedict[str(qid)]['JOBID'] == str(jobid):
      del dequedict[str(qid)]

  hsize=len(dequedict)
  if hsize == 0:
    os.unlink(quefile_lockfpath)
    return 0

  # re-indexing the hash
  temph={}
  num=0
  for key in sorted([int(x) for x in dequedict.keys()]):
    num += 1
    try:
      temph[str(num)]=dequedict[str(key)]
    except:
      raise

  dequedict={}
  logger.debug("Reindexed dictionary %s" % temph)
  dequedict=temph


  # updating table after dequeue step and reindexing
  with open(quefile, "w") as myfile:
    for key in sorted([int(x) for x in dequedict.keys()]):
      if 'PRODUCT' in dequedict[str(key)] and 'CLINE' in dequedict[str(key)] and \
          'TIMESTAMP' in dequedict[str(key)] and 'JOBID' in dequedict[str(key)] and \
          'ARCH' in dequedict[str(key)] and 'STATUS' in dequedict[str(key)] and 'PQUE' in dequedict[str(key)]:
        val="%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % \
            (key, dequedict[str(key)]['PRODUCT'], \
             dequedict[str(key)]['CLINE'], dequedict[str(key)]['TIMESTAMP'], \
             dequedict[str(key)]['JOBID'], dequedict[str(key)]['ARCH'], \
             dequedict[str(key)]['STATUS'], dequedict[str(key)]['PQUE'])
        myfile.write(val)
  
  os.unlink(quefile_lockfpath)
  logger.debug("Exiting dequetable_at_abort")
  return 0
  
def get_config_value(configs, name, default=None):
  for c in configs:
    if name in c:
      return c[name]
  return default

def init_verfication():
  ''' Check all the pre-requisite '''
  lockbin='/usr/bin/lockfile'
  stat={}
  if not os.path.exists(lockbin):
    stat['LOCKFILE']='Lock executable not present'
  if not os.path.exists(os.path.join(BASE_DIR, 'globalqdir')):
    stat['QUEDIR']='Quedir is missing'
    try:
      os.makedirs(os.path.join(BASE_DIR, 'globalqdir'))
    except OSError as e:
      if e.errno != e.EEXIST:
        raise e
      pass
  global post
  post='/usr/bin/curl'
  if not os.path.exists(post):
    stat['POSTOOL']='Posting utility not found'
   	
  brk=0
  if len(stat) > 0:
    for k in stat.keys():
      logger.info("Results of validation:\n")
      logger.warn("Validation %s found error: %s" % ( k, stat[k] ))
    sys.exit(1)
  else:
    logger.info("Validation was found ..........OK")
	
def get_vra_capacity():
  ''' Check for vRA capacity '''
  state_fpath = os.path.join(BASE_DIR, 'globalqdir', 'state.dat')
  state_lockfile = os.path.basename(state_fpath) + '.lock'
  state_lockfpath = os.path.join(BASE_DIR, 'globalqdir', state_lockfile)
  
  if os.path.exists(state_lockfpath):
    lock=1
    while lock:
      time.sleep(2.0)
      if not os.path.exists(state_lockfpath):
        lock=0
  cmd='/usr/bin/lockfile -10 ' + state_lockfpath
  os.system(cmd)
  
  flag=0
  ret=0 # defult return stay in queue
  logger.debug("Calling APIAuthapp .....")
  obj=APIAuthapp()
  
  logger.debug("Get what status check status to verify...")

  val=obj.get_status_check()
  logger.debug("Check for the status "+val)

  logger.debug("Get vra status from server......")
 
  stcnt=obj.get_vratatus(val)

  with open(state_fpath, 'w') as sd:
    sd.write(str(stcnt))

  ccnt=obj.get_clonecnt()

  # check current status vs uppper limit
  if stcnt <= ccnt:
    ret=1
  os.unlink(state_lockfpath)

  return ret

def process_request(jobid, quefile, pque=None):
  ''' This will process individual request coming from the jenkins '''
  msg01='''
        Your submitted is job, and will be serve as First Come First Serve basis
        Your job may waits for several minutes
        Duration of wait time depends on queue length
        Please be patience ..... no priority cases
        Do not abort the jobs/s.
        '''
  print ("\n")
  print (msg01)
  print ("\n")
  logger.debug("Priority user type: %s" % pque)
  flag = 1
  cnt = 0
  while flag:
    cnt += 1
    if cnt == 1:
      print ("\n")
      print ("Your job [ %s ] is waiting in queue" % jobid)
    time.sleep(30.0)
    enquejobs(jobid, quefile, pque)
    r=get_vra_capacity()
    if r == 1:
      dequeue_table(quefile)
      if str(resumeid) == str(jobid):
        print ("Waiting time for [ JOBID %s ] is over" % jobid)
        flag=0    
        break

	  
  if flag == 0:
    return "POP"
 
def release_jobs():
  ''' Release job to jenkins '''
  logger.info("Product:"+ options.product)
  logger.info("ARCH: %s" % options.arch)
  logger.info("Rtest:%s" % options.rtest)
  logger.info("QAUPD: %s " % options.qaupd)
  logger.info("EDITION: %s" % options.edition)
  logger.info("CLINE:"+ options.cline)
  
  import jenkins
  JENKINURL = get_jenkins_url()
  server = jenkins.Jenkins(JENKINURL)
  
  data={}
  if options.product == 'project':
    if options.qaupd:
      updopt = '--qaupdate'
    if options.changeconfig:
      chcong = options.changeconfig
    if options.edition:
      edition = options.edition 
    if options.arch:
      mtype = options.arch
    if options.cline:
      cline = options.cline
    if options.rtest:
      rtest = options.rtest
    if options.clist:
      clist = options.clist

    jobname = 'qa-Projcomp-' + mtype + '-cloud'
    logger.debug("Create dictionary of arguments")
    data = { 'clist': clist, 'rtests': rtest, 'update_options': updopt, 'change_config': chcong, 'edition': edition, 'mtype': mtype, 'cline': cline } 

    #triurl = post + ' -k -s ' + JENKINURL + '/job/' + jobname + '/buildWithParameters?' + 'clist=' + clist + '&' + 'rtests=' + rtest + '&' + 'update_options=' + updopt + '&' + 'change_config=' + chcong + '&' + 'edition=' + edition + '&' + 'mtype=' + mtype + '&' +  'cline=' + cline + '&' + 'token=PollingQueJobs'
  if options.product == 'nast':
    if options.qaupd and options.rerun:
      updopt = '--qaupdate,--rerun'
    elif options.qaupd:
      updopt = '--qaupdate'
    elif options.rerun:
      updopt = '--rerun'  
    if options.changeconfig:
      chcong = options.changeconfig
    if options.arch:
      mtype = options.arch
    if options.rtest:
      rtest = options.rtest
    if options.clist:
      clist = options.clist
    if options.cline:
      cline = options.cline
	  
    if options.rtest == 'doctest':
      jobname = 'qa-Nastran-' + cline.upper() + '-' + mtype + '-v16-cloud-doctest'
    else:
      if options.cline == 'NASTRAN_CDE':
        jobname = 'qa-Nastran-' + cline.upper() + '-' + mtype + '-v17-cloud'
      else:
        jobname = 'qa-Nastran-' + cline.upper() + '-' + mtype + '-v16-cloud'
	  
    logger.debug("Create dictionary of arguments")
    data = { 'clist': clist, 'rtests': rtest, 'update_options': updopt, 'change_config': chcong }

  if options.product == 'dytran':
    if options.qaupd:
      updopt = '--binrt,--qaupdate'
    else:
      updopt = '--binrt '
    if options.changeconfig:
      chcong = options.changeconfig
    if options.arch:
      mtype = options.arch
    if options.rtest:
      rtest = options.rtest
    if options.clist:
      clist = options.clist
    if options.cline:
      cline = options.cline	

    jobname = 'qa-Dytran-' + cline.upper() + '-' + mtype + '-v16-cloud'
    logger.debug("Create dictionary of arguments")
    data = { 'clist': clist, 'rtests': rtest, 'update_options': updopt, 'change_config': chcong }

  if options.product == 'marc' or \
        options.product == 'mentat':
    if options.changeconfig:
      chcong = options.changeconfig
    if options.edition:
      edition = options.edition 
    if options.arch:
      mtype = options.arch
    if options.cline:
      cline = options.cline
    if options.rtest:
      rtest = options.rtest
    if options.clist:
      clist = options.clist
    if options.flavor:
      cde = options.flavor
    jobname = 'qa-MarcMentat-Generic-cloud'
    logger.debug("Create dictionary of arguments")
    data = { 'clist': clist, 'rtests': rtest, 'mtype': mtype, 'cline': cline, 'edition': edition, 'product': options.product, 'cde': cde }
    #print "DATA: %s" % data
  if options.product == 'pat':
    if options.changeconfig:
      chcong = options.changeconfig
    if options.edition:
      edition = options.edition 
    if options.arch:
      mtype = options.arch
      if mtype.startswith("win"):
        mtype = 'SCONS-' + mtype
    if options.cline:
      cline = options.cline
    if options.rtest:
      rtest = options.rtest
    if options.clist:
      clist = options.clist
    if options.qaper:
      qlpercent=options.qaper
    if options.qaupd:
      qaupdate='yes'
    if options.maxmcs:
      maxmcs=options.maxmcs

    if options.job == 'CLS':  
      jobname = 'qa-Patran-' + cline.upper() + '-' + mtype + '-' + 'CLS' + '-cloud'
    elif options.job == 'SE':
      jobname = 'qa-Patran-' + cline.upper() + '-' + mtype + '-' + 'SE' + '-cloud'
    else:
      jobname = 'qa-Patran-' + cline.upper() + '-' + mtype + '-cloud'
    logger.debug("Create dictionary of arguments")
    data = { 'clist': clist, 'rtests': rtest, 'rtest_version_label': '0-V22', 'edition': edition, 'max_machines': maxmcs, 'qaupdate': qaupdate, 'qlpercent': qlpercent }
	
  if options.product == 'adams':
    if options.clist:
      clist = options.clist
    if options.rtest:
      rtest = options.rtest
    if options.qaupd:
      qaupdate = '--qaupdate'
    if options.changeconfig:
      chcong = options.changeconfig
    if options.arch == 'win64':
      mtype='win7'
    if options.arch == 'win10':
      mtype='win10'
    if options.arch == 'linux64_rhe67':
      mtype='linux64_rhe67'
    if options.arch == 'linux64_rhe71':
      mtype='linux64_rhe71'
    if options.arch == 'linux64_rhe73':
      mtype='linux64_rhe73'
    if options.arch == 'linux64_suse11sp3':
      mtype='linux64_suse11sp3'

    if options.cline:
      cline = options.cline
  
    jobname = 'qc-Adams-' + cline.upper() + '-' + mtype + '-v16-cloud'
    logger.debug("Create dictionary of arguments")
    data = { 'clist': clist, 'rtests': rtest, 'update_options': qaupdate, 'change_config': chcong }

  	
  print ("QC with jobs name %s is send for execution" % jobname)
  if len(data) > 0:
    try:
      nbld_no = server.get_job_info(jobname)['nextBuildNumber']
      val=server.build_job(jobname, data, token='PollingQueJobs')
      #print "Hello"
    except IOError, e:
      print ("Found error %s" % e)
      raise e
    else:
      print ("############ Thank you for your support ############")
      fnmsg = JENKINURL + "/job/" + jobname + "/" + str(nbld_no) + "/console"
      print ("You can monitor the latest job activity from the link: %s" % fnmsg)
  else:
    print ("Parameters are empty")

def sigterm_handler(signal, frame):
  ''' save the state here or do whatever you want '''
  logger.info('You like aborting garcefully !! bye bye')
  dequetable_at_abort()
  sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)

def main():
  ''' Main function starts here '''
  
  args = parse_options(sys.argv[1:])
  if options.state == None:
    option = opt = value = parser = 1
    sys.exit()
  global quefile
  global jobid
  quefile = os.path.join(BASE_DIR, 'globalqdir', 'queue_status.dat')
  init_verfication()
  jobid = os.getpid()
  logger.debug("Procees id: %s" % jobid)
  pque="" 
  if not options.iprior:
    vipass = os.path.join(BASE_DIR, 'globalqdir', 'vipticket.txt')
    if not os.path.exists(vipass):
      logger.debug("---- Skip Express Token Entry ----")
      pque = 'GEN'
    else:
      with open(vipass, 'r') as vip:
        content = f.readlines()
      # you may also want to remove whitespace characters like `\n` at the end of each line
      content = [x.strip() for x in content]
      pque = content[0]
  else:
    pque = options.iprior
        
  #if not options.clist or 
  msg02='''
        Disclaimer: 
              Job queue is based on first come first serve basis, job comes in queue will be serve first. 
              Please avoid aborting queuing job which may leads to instability of Queuing system.
              Check the activity to below job url to actvity of jobs run.
        ''' 
  rc=process_request(jobid, quefile, pque)
  if rc == "POP":
    print (msg02)
    print ("\n")
    print("You jobs with process id %s is released from queue" % resumeid)
    release_jobs()
  
if __name__ == "__main__":
  main()



