import sublime
import sublime_plugin
import re
import os
import fnmatch
import time
from Odin import completer


class OdinCompletions(sublime_plugin.EventListener):
  # when filtering for user dirs exclude these. Note that 'libs' is excluded only because 'projects' is in 'shared' temporarily
  exclude_dirs = set(['.git', 'libs'])
  alias_to_module = dict()

  import_pattern = re.compile(r'(import\s.*\n)')
  package_pattern = re.compile(r'package\s(.*)')
  core_module_pattern = re.compile(r'import\s([a-zA-Z]+|)\s*\"(?:core:)+(.*?)\"')
  shared_module_pattern = re.compile(r'import\s([a-zA-Z]+|)\s*\"(?:shared:)+(.*?)\"')
  local_module_pattern = re.compile(r'import\s([a-zA-Z]+|)\s*\"(?:[a-zA-Z0-9]+\/)+(.*?)\"')

  definition_pattern = re.compile(r'\b\w+\s*:[\w\W]*?[{;]')
  struct_pattern = re.compile(r'(\b\w+)\s*::\s*struct\s*[\w\W]*?[{;]')
  line_comment_pattern = re.compile(r'//.*?(?=\n)')
  proc_pattern = re.compile(r'\b(\w+)\s*:\s*[:=]\s*proc\(([\w\W]*?)\)\s*(?:->\s*(.*?)\s)?')
  proc_differentiator_pattern = re.compile(r'proc\(.*?\)')
  proc_params_pattern = re.compile(r'(?:^|)\s*([^,]+?)\s*(?:$|,)')

  current_module = ''
  included_core_modules = []
  included_local_modules = []
  included_shared_modules = []
  before_dot = None

  built_in_procs = ["len()", "cap()", "size_of()", "align_of()", "offset_of()", "typeid_of()", "type_of()", "type_info_of()", "swizzle()", "complex()", "real()", "imag()", "conj()", "expand_to_tuple()", "min()", "max()", "abs()", "clamp()", "#assert", "#location"]

  def alias_for_module(self, module):
    for k, v in self.alias_to_module.items():
      if v == module:
        return k
    return module

  def view_is_odin(self, view):
    self.view = view
    settings = view.settings()

    if settings != None:
      syntax = settings.get('syntax')
      if syntax != None:
        if syntax.find('odin.sublime-syntax') >= 0:
          return True

    path = view.file_name()

    if path != None and path[-5:].lower() == '.odin':
      return True

    return False

  def get_all_odin_file_paths(self):
    paths = set()
    window = sublime.active_window()

    word_before_dot = self.alias_to_module[self.before_dot] if self.before_dot in self.alias_to_module else self.before_dot

    # use this data to filter so we dont pile on unecessary files to parse
    is_core_module_completion = word_before_dot in self.included_core_modules
    is_shared_module_completion = word_before_dot in self.included_shared_modules
    is_user_module_completion = word_before_dot in self.included_local_modules
    is_var_field_access = word_before_dot != None and not is_core_module_completion and not is_user_module_completion and not is_shared_module_completion

    if not is_core_module_completion and not is_shared_module_completion and not is_var_field_access:
      # Get odin file paths from all open folders
      for folder in window.folders():
        for root, dirs, files in os.walk(folder):
          dirs[:] = list(filter(lambda x: not x in self.exclude_dirs, dirs))
          for file in fnmatch.filter(files, '*.odin'):
            file_path = os.path.join(root, file)
            paths.add(file_path)

      # Load all open odin files from views in case they're external files
      # for view in window.views():
      #   file_path = view.file_name()

      #   if file_path != None and file_path[-5:] == '.odin' and not file_path in paths:
      #     paths.add(file_path)

    if is_shared_module_completion and not is_var_field_access:
      # include any imported shared modules
      if len(self.included_shared_modules) > 0:
        odin_shared_path = os.path.expanduser('~/odin/shared')
        for root, dirs, files in os.walk(odin_shared_path):
          root_dir = os.path.basename(root)
          if root_dir in self.included_shared_modules:
            for file in fnmatch.filter(files, '*.odin'):
              paths.add(os.path.join(root, file))

    if is_core_module_completion and not is_var_field_access:
      # include any imported core modules
      if len(self.included_core_modules) > 0:
        odin_lib_path = os.path.expanduser('~/odin/core')
        for root, dirs, files in os.walk(odin_lib_path):
          root_dir = os.path.basename(root)
          if root_dir in self.included_core_modules:
            # special care for os
            if root_dir == 'os':
              paths.add(os.path.join(root, 'os.odin'))
            else:
              for file in fnmatch.filter(files, '*.odin'):
                paths.add(os.path.join(root, file))

    # if we have some module prefix then filter so we only include files in that module
    if (is_core_module_completion or is_user_module_completion or is_shared_module_completion) and not is_var_field_access:
      filter_txt = '*' + word_before_dot + '/*.odin'
      paths = fnmatch.filter(paths, filter_txt)

    return paths

  def get_file_contents(self, file_path):
    file_view = sublime.active_window().find_open_file(file_path)

    if file_view == None:
      with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()
    else:
      entire_buffer = file_view.find('[\w\W]*', 0)

      if entire_buffer == None:
        return ''
      else:
        return file_view.substr(entire_buffer)

  def strip_block_comments(self, odin_text):
    non_comments = []

    comment_end_index = 0
    block_comment_depth = 0

    for i in range(len(odin_text)):
      if odin_text[i:i+2] == '/*':
        if block_comment_depth == 0:
          non_comment = odin_text[comment_end_index:i]
          non_comments.append(non_comment)
        block_comment_depth += 1
      elif odin_text[i-2:i] == '*/':
        block_comment_depth -= 1
        if block_comment_depth == 0:
          comment_end_index = i
        if block_comment_depth < 0:
          block_comment_depth = 0

    non_comments.append(odin_text[comment_end_index:])
    return ''.join(non_comments)

  def strip_line_comments(self, odin_text):
    return self.line_comment_pattern.sub('', odin_text)

  def strip_imports(self, odin_text):
    return self.import_pattern.sub('', odin_text)

  def make_completions_from_proc_components(self, proc_name, params, return_type, file_name):
    trigger = proc_name + '('
    result = proc_name + '('

    if len(params) > 0:
      for p in range(len(params)):
        if p > 0:
          trigger += ', '
          result += ', '

        trigger += params[p]
        result += '${' + str(p+1) + ':' + params[p] + '}'

    trigger += ')'
    result += ')'

    if return_type != None:
      trigger += ' -> ' + return_type

    trigger += '\t ' + file_name

    # proc completion
    completions = [[trigger, result]]

    # TODO: not sure these are required. they make the results too noisy
    # param completions
    # for param in params:
    #   completion = self.make_completion_from_variable_definition(param, file_name)
    #   completions.append(completion)

    return completions

  def extract_definitions_from_text(self, odin_text):
    defs = self.definition_pattern.findall(odin_text)
    return list(set(defs))

  def make_completions_from_proc_definition(self, definition, file_name):
    match = self.proc_pattern.match(definition)
    if match == None:
      return []
    groups = match.groups()

    proc_name = groups[0]
    params_str = groups[1]
    return_type = groups[2]

    params_list = self.proc_params_pattern.findall(params_str)

    # Handle the case of empty space inside parentheses
    if len(params_list) == 1 and params_list[0].strip() == '':
      params_list = []

    return self.make_completions_from_proc_components(proc_name, params_list, return_type, file_name)

  def make_completion_from_variable_definition(self, definition, file_name):
    colon_index = definition.find(':')
    identifier = definition[:colon_index].strip()
    return [identifier + '\t ' + file_name, identifier]

  def get_completions_from_file_path(self, path):
    contents = self.get_file_contents(path)
    contents = self.strip_imports(contents)
    # Currently unused in order to maximize speed
    # contents = self.strip_block_comments(contents)
    # contents = self.strip_line_comments(contents)

    definitions = self.extract_definitions_from_text(contents)

    completions = []
    file_name = os.path.split(path)[1]

    for definition in definitions:
      if self.proc_differentiator_pattern.search(definition) == None:
        struct_match = self.struct_pattern.match(definition)
        if struct_match != None:
          struct_name = struct_match.groups()[0]
          completions.append([struct_name + '\t struct', struct_name])

        # TODO: this is a bit too loosey-goosey including every variable declaration
        #completion = self.make_completion_from_variable_definition(definition, file_name)
        #print('[[' + definition + ']] ---- ' + completion[0])
        #completions.append(completion)
      else:
        completions += self.make_completions_from_proc_definition(definition, file_name)

    return completions

  # return True if the next char is empty or a newline and all the previous chars are valid proc/var name chars up to the '.'
  def is_dot_completion(self, file_view, loc):
    # next char should be some type of space, ie we are not in a word typing
    next_char = file_view.substr(sublime.Region(loc, loc + 1))
    if next_char not in ['\n', '', ' ']:
      return False

    # walk backwards until we find a '.'. If we hit a non-proc/var char bail out since this isnt a completion
    curr_line_region = file_view.line(loc)
    while loc > curr_line_region.begin():
      char = file_view.substr(sublime.Region(loc - 1, loc))
      if char == '.':
        return True
        break;

      if char.isalnum() or char == '_':
        loc -= 1
      else:
        return False
        break;

  def extract_includes(self):
    contents = self.get_file_contents(sublime.active_window().active_view().file_name())
    self.current_module = self.package_pattern.findall(contents)[0]
    core_modules = self.core_module_pattern.findall(contents)
    shared_modules = self.shared_module_pattern.findall(contents)
    local_modules = self.local_module_pattern.findall(contents)

    for mod in core_modules:
      module = os.path.basename(os.path.normpath(mod[1]))
      alias = mod[0] or module
      self.alias_to_module[alias] = module
      self.included_core_modules.append(module)

    for mod in shared_modules:
      module = os.path.basename(os.path.normpath(mod[1]))
      alias = mod[0] or module
      self.alias_to_module[alias] = module
      self.included_shared_modules.append(module)

    for mod in local_modules:
      module = os.path.basename(os.path.normpath(mod[1]))
      alias = mod[0] or module
      self.alias_to_module[alias] = module
      self.included_local_modules.append(module)

  def on_query_completions(self, view, prefix, locations):
    # cleanup before we start
    self.alias_to_module.clear()
    self.included_core_modules.clear()
    self.included_shared_modules.clear()
    self.included_local_modules.clear()
    self.before_dot = None

    start_time = time.time()

    if not self.view_is_odin(view):
      return None


    # extract the current text if there is a '.' and get the previous word to see if it matches a package
    file_view = sublime.active_window().find_open_file(view.file_name())
    curr_line_region = file_view.line(locations[0])
    curr_line = file_view.substr(curr_line_region).strip()

    # this needs to check if the '.' is not just in the line but connected to the text we are typing
    if '.' in curr_line and self.is_dot_completion(file_view, locations[0]):
      self.before_dot = curr_line.rsplit('.', 1)[0]
    else:
      self.before_dot = None

    self.extract_includes()

    paths = self.get_all_odin_file_paths()
    completions = []

    # if we have not . in the text on the current line add the included module names as completions
    if self.before_dot == None:
      for mod in self.included_local_modules:
        completions.append(['Module: ' + mod, self.alias_for_module(mod)])
      for mod in self.included_core_modules:
        completions.append(['Module: ' + mod, self.alias_for_module(mod)])
      for mod in self.included_shared_modules:
        completions.append(['Module: ' + mod, self.alias_for_module(mod)])
      for proc in self.built_in_procs:
        completions.append([proc + '\tBuilt-in', proc])

    for path in reversed(list(paths)):
      completions += self.get_completions_from_file_path(path)

    # Report time spent building completions before returning
    delta_time_ms = int((time.time() - start_time) * 1000)
    message = 'Odin autocompletion took ' + str(delta_time_ms) + 'ms. Completions: ' + str(len(completions)) + '. Paths: ' + str(len(paths))
    view.window().status_message(message)

    return completions


