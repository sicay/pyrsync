#! /usr/local/bin/python

__version__ = "0.1"
__author__ = "Maxime Cayer"
__licence__ = "GNU GPL 2"

##
#
# Python Modules import
#
##

from os import mkdir, chdir, path
from os.path import exists, join
from sys import exit, argv
from datetime import datetime
from subprocess import call, list2cmdline
import logging
import json

##
#
# Script configuration
#
##

HOME = path.dirname(argv[0])
CONFIG = "pyrsync.json"
DB_DUMP_DIR = join(HOME,"databases")
RSYNC = "/usr/bin/rsync"
RSYNC_MODE_PATH = 1
RSYNC_MODE_MODULE = 2
RSYNC_SEPARATORS = {
	RSYNC_MODE_PATH:":",
	RSYNC_MODE_MODULE:"::"
	}
LOG_FILENAME = "pyrsync.log"
logging.basicConfig(filename=join(HOME,LOG_FILENAME),level=logging.DEBUG,format='%(levelname)s : %(asctime)s : %(message)s')
config = None

##
#
# Functions
#
##

def verify_env():
	global config
	
	if not exists(DB_DUMP_DIR):
		try:
			mkdir(DB_DUMP_DIR)
		except Exception, e:
			logging.error("Can't create database dump dir : "+str(e))
			return False
	
	if not exists(join(HOME,CONFIG)):
		logging.error("Config file not found")
		return False
	
	try:
		f = open(join(HOME,CONFIG))
		config = json.load(f)
		f.close()
	except Exception, e:
		logging.error("Can't read config : "+str(e))
		return False
	
	if "notification" not in config:
		logging.error("Keyword 'notification' not found in config")
		return False
	
	if "hosts" in config:
		if len(config['hosts']) == 0:
			logging.error("No hosts found for synchronisation")
			return False
	else:
		logging.error("Keyword 'hosts' not found in config")
		return False
	
	if "databases" in config:
		if len(config['databases']) > 0:
			try:
				call("mysqldump")
			except OSError, e:
				logging.error("Can't call mysqldump, database backup not possible : "+str(e))
				return False
		else:
			logging.info("No databases found to backup")
	else:
		logging.error("Keyword 'databases' not found in config")
		return False
	
	if "directories" in config:
		if len(config['directories']) == 0:
			logging.info("No directories found to be rsynced")
	else:
		logging.error("Keyword 'directories' not found in config")
		return False
	
	if "exclusions" in config:
		if len(config['directories']) == 0:
			logging.info("No directories found to be excluded")
	else:
		logging.error("Keyword 'exclusions' not found in config")
		return False
	
	return True

def backup_database(db):
	sql_file = join(DB_DUMP_DIR,str(db["name"])+".sql")
	with open(sql_file, "w") as outfile:
		logging.info("Backup of database "+str(db["name"]))
		call(["mysqldump","-u",str(db['username']),"-h","localhost","--password="+str(db['password']),"--skip-lock-tables",str(db["name"])], stdout=outfile)
		logging.info("End of database backup")

def get_rsync_options(host_config):
	global config
	
	options = []
	
	# RSYNC options
	short_options = "-"
	long_options = []
	
	for opt in host_config['options']:
		if len(opt) == 1:
			if host_config['options'][opt] == None:
				short_options += opt
			else:
				long_options.append("-"+opt+" '"+host_config['options'][opt]+"'")
		else:
			if host_config['options'][opt] == None:
				long_options.append("--"+opt)
			else:
				long_options.append("--"+opt+"="+host_config['options'][opt])
	
	options.append(short_options)
	options = options+long_options
	
	# Directories to synchronize
	if len(config['databases']) > 0:
		options.append(DB_DUMP_DIR)
	
	if len(config['directories']) > 0:
		for path in config['directories']:
			options.append(path)
	
	# Connection to host
	connection = (host_config['username']+"@"
		+host_config['host']
		+RSYNC_SEPARATORS[host_config['mode']]
		+host_config['path'])
	
	options.append(connection)
	
	# Directories to exclude
	if len(config['exclusions']) > 0:
		for path in config['exclusions']:
			options.append("--exclude="+path)
	
	return options

def sync():
	global config
	
	for host in config['hosts']:
		logging.info("Syncing to host "+str(host["name"]))
		
		options = get_rsync_options(host)
		cmd = [RSYNC]+options
		
		call(cmd)
		
		logging.info("Synchronisation complete")

def main():
	global config
	
	chdir(HOME)
	
	logging.info("Execution beginning")
	
	if verify_env():
		if config != None:
			for db in config['databases']:
				backup_database(db)
			
			if len(config['databases']) > 0 or len(config['directories']) > 0:
				sync()
		
	logging.info("Execution end")

##
#
# Main
#
##

if __name__ == "__main__":
	main()

