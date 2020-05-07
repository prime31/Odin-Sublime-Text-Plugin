import re
import os
import fnmatch

# stores the completions list by package name
class CompletionCache(object):
	completions_by_package = dict()

	def invalidate_completions(self, package):
		self.completions_by_package.pop(package, None)

	def has_completions(self, package):
		return package in self.completions_by_package

	def set_completions(self, package, completions):
		self.completions_by_package[package] = completions

# dictionary keyed by the package name to the full path. 'sdl' -> 'shared:engine/libs/sdl'
package_to_path = dict()
completions_cache = CompletionCache()


# captures: 1 -> name, 2 -> params, 3 -> return types
proc_return_pattern = re.compile(r'\b(\b[^_][\w_]+[\w\d_]*\b)\s*[:]\s*[:]\s*(?:inline|no_inline|)\s*proc\s*(?:|\s[\"a-z]+\s)\(([\w\W]*?)\)\s*(?:(?:->|where.*?)\s*(.*?))?(?:{|-|;)')
# captures: 1 -> name, 2 -> overloaded procs
proc_overload_pattern = re.compile(r'\b(\b[\w_]+[\w\d_]*\b)\s*::\s*proc\s*{(.*?)};')
# captures: 1 -> name, 2 -> type/keyword
type_pattern = re.compile(r'\b(\b[\w_]+[\w\d_]*\b)\s*[:]\s*[:]\s*(struct|union|enum|bit_field|bit_set|distinct)')
# captures: 1 -> name
const_pattern = re.compile(r'([A-Z0-9_]+)\s+::\s+(?!proc|distinct|enum|bit_set)\w+.*?;')
# finds all the commas that are not surrounded by parens (used to filter out a proc with muliple params as a param to a proc)
param_delim_pattern = re.compile(r',(?![^(]*\))')


def reindex_all_package_names(view, current_folder):
	package_to_path.clear()

	# only include the active files folder if it isnt in the shared folder
	if '/odin/shared' not in current_folder:
		get_all_packages_in_folder(current_folder)
	odin_path = os.path.expanduser(view.settings().get('odin_install_path', '~/odin'))
	get_all_packages_in_folder(os.path.join(odin_path, 'core'), 'core')
	get_all_packages_in_folder(os.path.join(odin_path, 'shared'), 'shared')


# prefix should be 'core' or 'shared' to indicate special folders else None
def get_all_packages_in_folder(path, prefix=None):
	for root, dirs, files in os.walk(path):
		dirs[:] = list(filter(lambda x: not x == '.git', dirs))
		if len(fnmatch.filter(files, '*.odin')) > 0:
			if prefix != None:
				folder = root[root.index(prefix):]
				package = os.path.basename(os.path.normpath(folder))
				folder = folder.replace('/', ':', 1)
				folder = folder.replace('\\', ':', 1)
				package_to_path[package] = folder
			else:
				# TODO: handle local, non-core/shared imports
				print('TODO: add support for local, non-core/shared imports')


def invalidate_completions(package):
	completions_cache.invalidate_completions(package)


def get_completions_from_file(package_or_filename, text):
	completions = get_type_and_const_completions(package_or_filename, text)
	matches = proc_return_pattern.findall(text)
	for m in matches:
		name = m[0]
		param_str = m[1].strip()
		retval = None if len(m[2].strip()) == 0 else m[2].strip()

		params = []

		# find all the relevant commas that we need to split on. This filter our commans inside a param with a type that is
		# a proc with multiple params itself.
		commas = []
		for pm in param_delim_pattern.finditer(param_str):
			commas.append(pm.start(0))

		if len(commas) > 0:
			commas.append(len(param_str))
			for i in range(len(commas)):
				start = commas[i - 1] + 1 if i > 0 else 0
				end = commas[i]
				params.append(param_str[start:end].strip())
		elif len(param_str):
			params.append(param_str)

		completions.append(make_completion_from_proc_components(name, params, retval, package_or_filename))

	matches = proc_overload_pattern.findall(text)
	for m in matches:
		name = m[0]
		overloads = m[1]

		# for overloads, we need to add completions for all the variants
		for proc in [x.strip() + '(' for x in overloads.split(',')]:
			for c in completions:
				if c[0].startswith(proc):
					new_completion = c[0].replace(proc, name + '(')
					new_insertion = c[1].replace(proc, name + '(')
					completions.append([new_completion, new_insertion])
					break
		completions.append([name + '     [proc overload, use a variant]\t' + package_or_filename, name + '(${0:overloads: ' + overloads + '})'])

	return completions


def get_type_and_const_completions(package_or_filename, text):
	completions = []
	matches = type_pattern.findall(text)
	for m in matches:
		completions.append(['{}\t{} {}'.format(m[0], m[1], package_or_filename), m[0]])

	matches = const_pattern.findall(text)
	for m in matches:
		completions.append([m + '\tconst', m])

	return completions


def make_completion_from_proc_components(proc_name, params, return_type, file_name):
	trigger = proc_name + '('
	result = proc_name + '('

	if len(params) > 0:
		for p in range(len(params)):
			if p > 0:
				trigger += ', '
				result += ', '

			trigger += params[p]
			result += '${' + str(p + 1) + ':' + params[p] + '}'

	trigger += ')'
	result += ')'

	if return_type != None:
		trigger += ' -> ' + return_type

	trigger += '\t ' + file_name

	# proc completion
	completion = [trigger, result]

	return completion
