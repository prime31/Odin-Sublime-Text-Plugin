# import sublime
# import sublime_plugin
import re
import os
import json
import subprocess


# JSON consits of two roots: packages and definitions. Some keys are optional, denoted with '?'.
# 	packages keys: name, fullpath, files (list)
#	definitions keys: package, name, filepath, line, column, file_offset, kind, type_kind?, type?, size?, align?
#		kinds: procedure group, constant, type name, variable, procedure
#		kinds without types: procedure group, constant
#		type_kinds: union, array, bit field, slice, dynamic array, bit set, struct, enum, procedure
#			structs: have an extra map 'data' with an array of fields in 'fields'


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
	packages = []
	procs_by_package = dict()
	types_by_package = dict()
	vars_by_package = dict() # includes the kinds constant and variable

	proc_params_pattern = re.compile(r'.*?proc.*?(\(.*?)$')

	def __init__(self, current_file):
		self.index_file(current_file)

	def index_file(self, current_file):
		output = subprocess.check_output(['odin', 'query', current_file, '-global-definitions'])

		js = json.loads(output.decode('utf-8'))
		packages = js['packages']
		definitions = js['definitions']

		for p in packages:
			if p['name'] == 'main':
				continue
			self.packages.append(p['name'])

		type_kind = []
		kinds = []
		types = []
		for d in definitions:
			package = d['package']
			name = d['name']
			kind = d['kind']
			typ = d.get('type')

			type_kind.append(d.get('type_kind'))
			kinds.append(kind)
			types.append(typ)

			if kind == 'type name':
				self.types_for_package(package).append([typ + '\t' + package, typ])
			elif kind == 'variable' or kind == 'constant':
				self.vars_for_package(package).append([name + '\t' + d.get('type_kind', package), name])
			elif kind == 'procedure':
				self.procs_for_package(package).append(self.gen_completion_for_proc(package, name, typ))

		type_kind_set = set(type_kind)
		kinds_set = set(kinds)
		types_set = set(types)
		#print(self.vars_by_package)

	def gen_completion_for_proc(self, package, name, sig):
		parts = list(map(lambda s:s.strip(), sig.split('->')))
		body = self.proc_params_pattern.findall(parts[0])[0]
		params = list(map(lambda s:s.strip(' ()'), body.split(',')))

		trigger = name + sig[sig.index('('):]
		result = name + '('

		if len(params) > 0:
			for p in range(len(params)):
				if p > 0:
					result += ', '
				result += '${' + str(p + 1) + ':' + params[p] + '}'
		result += ')'

		return [[trigger + '\t' + package]]

	def procs_for_package(self, package):
		if not package in self.procs_by_package:
			self.procs_by_package[package] = []
		return self.procs_by_package[package]

	def types_for_package(self, package):
		if not package in self.types_by_package:
			self.types_by_package[package] = []
		return self.types_by_package[package]

	def vars_for_package(self, package):
		if not package in self.vars_by_package:
			self.vars_by_package[package] = []
		return self.vars_by_package[package]




c = Completer('/Users/mikedesaro/odin/shared/engine/input/input.odin')