import re


cache = CompletionCache()

# caps: 1 -> name, 2 -> params, 3 -> return types
proc_return_pattern = re.compile(r'\b(\b[\w_]+[\w\d_]*\b)\s*[:]\s*[:]\s*(?:inline|no_inline|)\s*proc\s*(?:|\s[\"a-z]+\s)\(([\w\W]*?)\)\s*(?:->\s*(.*?))?(?:{|-|;)')
# caps: 1 -> name, 2 -> type/keyword
type_pattern = re.compile(r'\b(\b[\w_]+[\w\d_]*\b)\s*[:]\s*[:]\s*(struct|union|enum|bit_field|bit_set)')
# finds all the commas that are not surrounded by parens (used to filter out a proc with muliple params as a param to a proc)
param_delim_pattern = re.compile(r',(?![^(]*\))')


def invalidate_completions(package):
	cache.invalidate_completions(package)


def get_completions_from_file(package_or_filename, text):
	completions = get_type_completions(package_or_filename, text)
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

	return completions


def get_type_completions(package_or_filename, text):
	completions = []
	matches = type_pattern.findall(text)
	for m in matches:
		completions.append(['{}\t{} {}'.format(m[0], m[1], package_or_filename), m[0]])

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





class CompletionCache(object):
	completions_by_package = dict()

	def invalidate_completions(self, package):
		self.completions_by_package.pop(package, None)

	def has_completions(self, package):
		return package in self.completions_by_package

	def set_completions(self, package, completions):
		self.completions_by_package[package] = completions
