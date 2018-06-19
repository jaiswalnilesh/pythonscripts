import os
import tempfile
import shutil
import logging
import platform
from vRADriver.utils.process import die


CONFIG_FILE = '.nofiles'

tempfiles = []

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


def cleanup_tempfiles():
    for tmpfile in tempfiles:
        try:
            os.unlink(tmpfile)
        except:
            pass


def get_config_value(configs, name, default=None):
    for c in configs:
        if name in c:
            return c[name]

    return default


def load_config_files(homepath):
    """Loads data from .cloudrc files."""
    def _load_config(path):
        config = {
            'TREES': {},
        }

        filename = os.path.join(path, CONFIG_FILE)

        if os.path.exists(filename):
            try:
                execfile(filename, config)
            except SyntaxError, e:
                die('Syntax error in config file: %s\n'
                    'Line %i offset %i\n' % (filename, e.lineno, e.offset))

            return config

        return None

    configs = []

    for path in walk_parents(os.getcwd()):
        config = _load_config(path)

        if config:
            configs.append(config)

    user_config = _load_config(homepath)
    if user_config:
        configs.append(user_config)

    return user_config, configs


def make_tempfile(content=None):
    """
    Creates a temporary file and returns the path. The path is stored
    in an array for later cleanup.
    """
    fd, tmpfile = tempfile.mkstemp()

    if content:
        os.write(fd, content)

    os.close(fd)
    tempfiles.append(tmpfile)
    return tmpfile


def walk_parents(path):
    """
    Walks up the tree to the root directory.
    """
    while os.path.splitdrive(path)[1] != os.sep:
        yield path
        path = os.path.dirname(path)

def removeDir(path):
	try:
		if os.path.isdir(path):
			#shutil.rmtree(path)
			if platform.system() == 'Windows':
				os.system('rmdir /S /Q \"{}\"'.format(path))
			else:
				shutil.rmtree(path)
	except IOError, e:
		die("Failed to remove: %s" % path)
	else:
		logging.info("Remove directory: %s" % path)		
		
def copyBuildDir(source, target):
	#""Copy the build to the target lcoation """
	#print("Source dir: %s" % source)
	#print("Target dir %s" % target)
	rc=0
	if not os.path.isdir(target):
		try:
			#os.makedirs(target)
			shutil.copytree(source, target)
		except IOError, e:
			print("Failed to copy target directory")
			rc=1
	else:
		#shutil.rmtree(target)
		print
		print "################################################"
		print("Found target, removing %s" % target)
		if platform.system() == 'Windows':
			os.system('rmdir /S /Q \"{}\"'.format(target))
		else:
			shutil.rmtree(target)
		try:
			shutil.copytree(source, target)
		except IOError, e:
			print("Failed to copy target directory")
			rc=1
			#rc=1
	#shutil.copy(source, target)
	return rc
		
def copyLogFile(source, target):
	rc=0
	if not os.path.isdir(target):
		try:
			os.makedirs(target)
			shutil.copy(source, target)
		except IOError, e:
			print("Failed to copy at target directory")
			rc=1
	return rc

