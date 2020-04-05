import re
import os
import time
import json
import subprocess


# JSON consists of two roots: packages and definitions. Some keys are optional, denoted with '?'.
# 	packages keys: name, fullpath, files (list)
#	definitions keys: package, name, filepath, line, column, file_offset, kind, type_kind?, type?, size?, align?
#		kinds: procedure group, constant, type name, variable, procedure
#		kinds without types: procedure group, constant
#		type_kinds: union, array, bit field, slice, dynamic array, bit set, struct, enum, procedure
#			structs: have an extra map 'data' with an array of fields in 'fields'


# completions come in a few different flavors based on the context of the cursor:
#	- naked: there is no previous '.' in the completion string. Completions here could be:
#		- procs in the current package
#		- types/constants in the current package
#		- module names (or aliases if used) for any imports
#		- local variable names
#	- dotted module: there is 'module.' and the word before the '.' is a module name or alias
#		- procs in the module
#		- types/constants in the module
#		- exposed globals in the module
#	- dotted non-module:
#		- most likely a local variable. Too hard to figure out its type so forget it.
class Completer(object):
	full_reindex_interval_secs = 60
	last_full_reindex_secs = -full_reindex_interval_secs # Ensure re-indexing happens on launch
	last_indexed_file = ''

	packages = []
	procs_by_package = dict()
	types_by_package = dict()
	vars_by_package = dict() # includes the kinds 'constant' and 'variable'

	proc_params_pattern = re.compile(r'.*?proc.*?(\(.*?)$')

	# we re-index if this is a different file than was last indexed or it has been longer than
	# full_reindex_interval_secs
	def needs_reindex(self, current_file):
		if self.last_indexed_file != current_file:
			self.last_indexed_file = current_file
			return True

		if time.time() - self.last_full_reindex_secs > self.full_reindex_interval_secs:
			return True
		return False

	def index_file(self, current_file):
		if not self.needs_reindex(current_file):
			return

		contents = open(current_file, 'r', encoding='utf-8').read()
		if contents.find('main :: proc') == -1:
			return

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
		self.last_full_reindex_secs = time.time()

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

		return [trigger + '\t' + package, result]

	def procs_for_package(self, package):
		if not package in self.procs_by_package:
			self.procs_by_package[package] = []
		else:
			self.procs_by_package[package].clear()
		return self.procs_by_package[package]

	def types_for_package(self, package):
		if not package in self.types_by_package:
			self.types_by_package[package] = []
		else:
			self.types_by_package[package].clear()
		return self.types_by_package[package]

	def vars_for_package(self, package):
		if not package in self.vars_by_package:
			self.vars_by_package[package] = []
		else:
			self.vars_by_package[package].clear()
		return self.vars_by_package[package]




#c = Completer()
#c.index_file('/Users/mikedesaro/odin/shared/engine/input/input.odin')