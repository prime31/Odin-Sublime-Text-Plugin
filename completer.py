import sublime
import sublime_plugin
import re
import os
import fnmatch

def fart():
	print('----------- fart')


# completions come in a few different flavors based on the context of the cursor:
#	- naked: there is no previous '.' in the completion string. Completions here could be:
#		- procs in the current package
#		- types in the package
#		- module names (or aliases if used) for any imports
#		- local variable names
#	- dotted module: there is 'module.' and the word before the '.' is a module name or alias
#		- procs in the module
#		- types in the module
#		- exposed globals in the module
#	- dotted non-module:
#		- most likely a local variable. Too hard to figure out its type so forget it.
class Completer(object):
	def fart(self):
		print('------- wha asflkjdf')
