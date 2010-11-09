#!/usr/bin/env python
import filecmp
import pickle
import os
import pprint
import argparse
import shutil
import sys

class ArgParser(argparse.ArgumentParser):
	def error(self, message):
		sys.stderr.write('error:%s\n'%message)
		self.print_help()
		sys.exit(2)

def recursive_scan(comparator, delay):
	if args.force_recheck:
		recheck(comparator)
	for filename in comparator.right_only: # these are files only in the backupdir
		filename = comparator.right+'/'+filename
		if not filename in diff_hash:	# ensure that file does not already exist in the list
			if args.verbose:
				print "adding file", filename, "to deletion index..."
			diff_hash[filename] = delay
	for subdir_comparator in comparator.subdirs.itervalues():
		recursive_scan(subdir_comparator, delay)

def shallow_scan(comparator, delay):
	if args.force_recheck:
		recheck(comparator)
	for filename in comparator.right_only:
		filename = comparator.right+'/'+filename
		if not filename in diff_hash:
			if args.verbose:
				print "adding file", filename, "to deletion index..."
			diff_hash[filename] = delay

def recheck(comparator):
	for filename in comparator.common:
		filename = comparator.right+'/'+filename
		if filename in diff_hash:
			if args.verbose:
				print "removing", filename, "from deletion index..."
			del diff_hash[filename]

def main():
	parser = ArgParser(description='Remove files from a backup directory X \
			days after deletion from the source directory.')
	parser.add_argument('-d', '--delay', metavar='X', type=int, default=30, \
			help='delay (in days) after which to delete extraneous files')
	parser.add_argument('source', nargs=1, type=str, \
			help='the source directory')
	parser.add_argument('backup', nargs=1, type=str, \
			help='the backup directory')
	parser.add_argument('-v', '--verbose', action='store_true',\
			help='increase verbosity')
	parser.add_argument('-f', '--force-recheck', action='store_true',\
			help='rechecks all files in the deletion index to ensure that they should be deleted. \
			useful if files were moved from the source directory and subsequently moved back to the source directory.')
	parser.add_argument('-r', '--recursive', action='store_true',\
			help='recursive mode')
	parser.add_argument('-t', '--test', action='store_true', \
			help='test mode - does not erase any files, but shows which files would be erased')
	parser.add_argument('--version', action='version', version='%(prog)s 1.1 by Zach Denton <zacharydenton@gmail.com>')
	global args
	global diff_hash
	args = parser.parse_args()

	source = os.path.realpath(args.source[0])
	backup = os.path.realpath(args.backup[0])
	list_location = source + '/.diff_list'
#	directory = '/'+user+'/Maildir'
#	maildir = '/home' + directory
#	backupdir = '/mail-backup' + directory 
#	list_location = '/home/'+user+'/.diff_list'

	# load data; decrement delete date of files to be changed
	if not args.test:
		try:
			print "attempting to load diff list from", list_location + "..."
			diff_list = open(list_location, 'r')
			diff_hash = pickle.load(diff_list)
			for filename, days_left in diff_hash.iteritems():
				# decrement date
				diff_hash[filename] -= 1
			diff_list.close()

		except:
			# file doesn't exist, so create an empty file
			open(list_location, 'w').close()
			diff_hash = {}
			pass
	else:
		args.verbose = True
		diff_hash = {}

	# scan directories for files that have been deleted
	try:
		print "generating diff list for", source, backup + "..."
		comparator = filecmp.dircmp(source, backup)
		if args.recursive:
			recursive_scan(comparator, args.delay)
		else:
			shallow_scan(comparator, args.delay)
	except OSError as e:
		# The backup directory doesn't exist. Skip this one.
		print e

	# delete files whose delete date is <= 0
	if not args.test:
		for filename, days_left in diff_hash.iteritems():
			if days_left <= 0:
				# remove the file from disk and from the list
				if args.verbose:
					print "deleting "+filename
				del diff_hash[filename]
				if os.path.isfile(filename):
					os.remove(filename)
				elif os.path.isdir(filename):
					shutil.rmtree(filename)


	# append those changed files to a list of files to be deleted (if they're not already there)
	if not args.test:
		print "saving diff list", list_location +  "..."
		diff_list = open(list_location, 'w')
		pickle.dump(diff_hash, diff_list)
		diff_list.close()
	if args.verbose:
		pprint.pprint(diff_hash)


if __name__ == '__main__':
	main()
