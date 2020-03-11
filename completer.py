import sublime
import sublime_plugin
import re
import os
import fnmatch

def fart():
	print('----------- fart')


# completions come in a few different flavors:
#	- naked: there is no previous '.' in the completion string. Completions here could be:
#		- local procs in the current file
#		- module names (or aliases if used)
class Completer(object):
	def fart(self):
		print('------- wha asflkjdf')
