import os
import subprocess
import sys
import platform
import tempfile
import logging
import re

from vRADriver.utils.process import die, execute

import os

SUFFIXES = {1000: ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
			1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']}



def makepath(*args):
    for directory_name in args:
        if not directory_name or os.path.exists(directory_name):
            continue
        makepath(os.path.dirname(directory_name))
        os.mkdir(directory_name)

def getArchType():
	if sys.platform.startswith('win'):
		if "64" in os.environ['PROCESSOR_IDENTIFIER']:
			mtype='win64'
		else:
			mtype='win32'
	elif os.name == 'posix' and platform.system() == 'Linux':
		if platform.architecture()[0] == '64bit':
			mtype='linux64'
		else:
			mtype='linux32'
	else:
		mtype='Unknown'

	return mtype

def banner(text, ch='=', length=90):
    """Return a banner line centering the given text.

        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> banner("MSC Software")
        '================================= MSC Software =================================='
        >>> banner("MSC Software", ch='-', length=50)
        '------------------- MSC Software --------------------'
        >>> banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        txt=prefix + ' ' + text + ' ' + suffix
        print txt
        #return prefix + ' ' + text + ' ' + suffix

def checkDiskspace(directory):
	"""
	Check the disk space at given disk
	"""	
	rc=""
	if platform.system() == 'Windows':
		import ctypes
		directory=re.sub('/', '\\\\', directory)
		print("Checking space at %s" % directory)
		free_bytes = ctypes.c_ulonglong(0)
		ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(directory), None, None, ctypes.pointer(free_bytes))
		free_space = free_bytes.value
		print("Free space available: %s " % approximate_size(free_space, False))
		if free_space > 10000000000:
			print("Free space seems to be ok")
		else:
			print("Insufficient disk space")
			rc=1
			return rc
		directory=tempfile.gettempdir()
		print("Checking space at %s" % directory)	
		free_bytes = ctypes.c_ulonglong(0)
		ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(directory), None, None, ctypes.pointer(free_bytes))
		free_space = free_bytes.value
		print("Free space available: %s " % approximate_size(free_space, False))
		if free_space > 5000000000:
			print("Free space in temp is ok")
		else:
			print("Insufficient space in Temp directory")
			rc=1
			return rc
	else:
		import statvfs
		print("Checking space at %s" % directory)
		stats = os.statvfs(directory)
		free_space = stats[statvfs.F_BSIZE] * stats[statvfs.F_BAVAIL]
		print("Free space available: %s " % approximate_size(free_space, False))
		if free_space > 10000000000:
			print("Free space seems to be ok")
		else:
			print("Insufficient disk space")
			rc=1
			return rc
		directory=tempfile.gettempdir()
		print("Checking space at %s" % directory)
		stats = os.statvfs(directory)
		free_space = stats[statvfs.F_BSIZE] * stats[statvfs.F_BAVAIL]
		print("Free space available: %s " % approximate_size(free_space, False))
		if free_space > 180000000:
			print("Free space in temp is ok")
		else:
			print("Insufficient space in Temp directory")
			rc=1
			return rc

def checkPerm():
   """
    Check permission on given drive
   """
   pass

def approximate_size(size, a_kilobyte_is_1024_bytes=True):
	"""Convert a file size to human-readable form.

	Keyword arguments:
	size -- file size in bytes
	a_kilobyte_is_1024_bytes -- if True (default), use multiples of 1024
                                if False, use multiples of 1000
    Returns: string
    """
	if size < 0:
		raise ValueError('number must be non-negative')
	multiple = 1024 if a_kilobyte_is_1024_bytes else 1000
	for suffix in SUFFIXES[multiple]:
		size /= multiple
		if size < multiple:
			return '{0:.1f} {1}'.format(size, suffix)

	raise ValueError('number too large')

	
