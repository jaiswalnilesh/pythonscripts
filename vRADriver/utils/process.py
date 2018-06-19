import logging
import os
import subprocess
#from subprocess import Popen, PIPE
import sys
from time import sleep
import json


def die(msg=None):
    """
    Cleanly exits the program with an error message. Erases all remaining
    temporary files.
    """
    from vCACTools.utils.filesystem import cleanup_tempfiles

    cleanup_tempfiles()

    if msg:
        print msg

    sys.exit(1)

def execute(command,
            env=None,
            split_lines=False,
            ignore_errors=False,
            extra_ignore_errors=(),
            translate_newlines=True,
            with_errors=True,
            none_on_ignored_error=False):
    """
    Utility function to execute a command and return the output.
    """
    if isinstance(command, list):
        logging.debug('Running: ' + subprocess.list2cmdline(command))
    else:
        logging.debug('Running: ' + command)

    if env:
        env.update(os.environ)
    else:
        env = os.environ.copy()

    env['LC_ALL'] = 'en_US.UTF-8'
    env['LANGUAGE'] = 'en_US.UTF-8'

    if with_errors:
        errors_output = subprocess.STDOUT
    else:
        errors_output = subprocess.PIPE

    if sys.platform.startswith('win'):
        p = subprocess.Popen(command,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=errors_output,
                             shell=False,
                             universal_newlines=translate_newlines,
                             env=env)
    else:
        p = subprocess.Popen(command,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=errors_output,
                             shell=False,
                             close_fds=True,
                             universal_newlines=translate_newlines,
                             env=env)
    if split_lines:
        data = p.stdout.readlines()
    else:
        data = p.stdout.read()

    rc = p.wait()

    if rc and not ignore_errors and rc not in extra_ignore_errors:
        die('Failed to execute command: %s\n%s' % (command, data))
    elif rc:
        logging.debug('Command exited with rc %s: %s\n%s---'
                      % (rc, command, data))

    if rc and none_on_ignored_error:
        return None

    return data

def execute_createvm(cmd):
    logging.debug('Inside execute_createvm: %s' % cmd)
    r = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    status=r.wait()
    p = r.communicate()
    if status != 0:
        logging.debug("value status: %d" % (status))
        logging.debug("value p[0]: %s" % (p[0]))
        logging.debug("value p[0]: %s" % (p[1]))
        logging.debug("value p[1]: %s" % (len(p[1])))
        logging.debug("value p[0]: %s" % (len(p[0])))
        logging.debug("Error: %s" % p[0].split('Error')[-1])
        sys.stdout.flush()
        if status == 1:
          if len(p[1]) > 0:
            return p[1]
          elif len(p[0]) > 0:
            return p[0]
          else:
            return status
    logging.debug('Return value in executeRequest: %s' % p[0])
    return p[0]

def execute_action(cmd):
    logging.debug("Inside executeRequst: %s" % cmd)
    r = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    status=r.wait()
    p = r.communicate()
    if status != 0:
        logging.debug("value status: %d" % (status))
        logging.debug("value p[1]: %s" % (p[1]))
        logging.debug("value p[0]: %s" % (p[0]))
        return p[1]
    logging.debug("Return value in executeRequest: %s" % p[0])
    return p[0]

