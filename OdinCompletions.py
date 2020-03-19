import sublime
import sublime_plugin
import re
import os
import glob
import fnmatch
import time
from Odin import completer
from Odin import parser


class OdinCompletions(sublime_plugin.EventListener):
  completer = completer.Completer()
  # when filtering for user dirs exclude these. Note that 'libs' is excluded only because 'projects' is in 'shared' temporarily
  exclude_dirs = set(['.git', 'libs'])
  alias_to_package = dict()

  import_pattern = re.compile(r'(import\s.*\n)')
  package_pattern = re.compile(r'package\s(.*)')
  core_package_pattern = re.compile(r'import\s(\w+|)\s*\"(?:core:)+(.*?)\"')
  shared_package_pattern = re.compile(r'import\s(\w+|)\s*\"(?:shared:)+(.*?)\"')
  local_package_pattern = re.compile(r'import\s(\w+|)\s*\"(?!.*?:)(\w+)+(.*?)\"')

  definition_pattern = re.compile(r'\b\w+\s*:[\w\W]*?(?:[{;]|[-]{3})')
  struct_pattern = re.compile(r'(\b\w+)\s*::\s*struct\s*[\w\W]*?[{;]')
  line_comment_pattern = re.compile(r'//.*?(?=\n)')
  proc_pattern = re.compile(r'\b(\w+)\s*:\s*[:=]\s*proc\(([\w\W]*?)\)\s*(?:->\s*(.*?)\s)?')
  proc_differentiator_pattern = re.compile(r'proc\(.*?\)')
  proc_params_pattern = re.compile(r'(?:^|)\s*([^,]+?)\s*(?:$|,)')

  # the package of the current file
  current_package = ''
  # the package we are completing (ie fmt.nnn would be 'fmt')
  search_package = None
  included_core_packages = []
  included_local_packages = []
  included_shared_packages = []
  before_dot = None

  built_in_procs = [
    ['make(array_map: Array_Map_Type, size: int) \tBuilt-in', 'make(${1:array_map: Array_Map_Type}, ${2:size: int})'],
    ['append(array_map: ^Array_Map_Type, arg: $E) \tBuilt-in', 'append(${1:array_map: Array_Map_Type}, ${2:arg: $E})']
  ]

  def alias_for_package(self, package):
    for k, v in self.alias_to_package.items():
      if v == package:
        return k
    return package

  def view_is_odin(self, view):
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

    word_before_dot = self.alias_to_package[self.before_dot] if self.before_dot in self.alias_to_package else self.before_dot

    # use this data to filter so we dont pile on unecessary files to parse
    is_core_package_completion = word_before_dot in self.included_core_packages
    is_shared_package_completion = word_before_dot in self.included_shared_packages
    is_local_package_completion = word_before_dot in self.included_local_packages
    is_var_field_access = word_before_dot != None and not is_core_package_completion and not is_local_package_completion and not is_shared_package_completion

    if word_before_dot == None and not is_var_field_access:
      paths.add(os.path.expanduser('~/odin/core/builtin/builtin.odin'))

      # self.current_package is where we will source our files from
      current_folder = os.path.dirname(sublime.active_window().active_view().file_name())
      for file in glob.glob(current_folder + '/*.odin'):
        paths.add(file)


    if is_local_package_completion and not is_var_field_access:
      if len(self.included_local_packages) > 0:
        curr_path = os.path.dirname(sublime.active_window().active_view().file_name())
        for root, dirs, files in os.walk(curr_path):
          dirs[:] = list(filter(lambda x: not x == '.git', dirs))
          root_dir = os.path.basename(root)
          if root_dir == word_before_dot and root_dir in self.included_local_packages:
            for file in fnmatch.filter(files, '*.odin'):
              paths.add(os.path.join(root, file))

    if is_shared_package_completion and not is_var_field_access:
      # include any imported shared packages
      if len(self.included_shared_packages) > 0:
        odin_shared_path = os.path.expanduser('~/odin/shared')
        for root, dirs, files in os.walk(odin_shared_path):
          dirs[:] = list(filter(lambda x: not x == '.git', dirs))
          root_dir = os.path.basename(root)
          if root_dir == word_before_dot and root_dir in self.included_shared_packages:
            for file in fnmatch.filter(files, '*.odin'):
              paths.add(os.path.join(root, file))

    if is_core_package_completion and not is_var_field_access:
      # include any imported core packages
      if len(self.included_core_packages) > 0:
        odin_lib_path = os.path.expanduser('~/odin/core')
        for root, dirs, files in os.walk(odin_lib_path):
          root_dir = os.path.basename(root)
          if root_dir == word_before_dot and root_dir in self.included_core_packages:
            # special care for os
            if root_dir == 'os':
              paths.add(os.path.join(root, 'os.odin'))
            else:
              for file in fnmatch.filter(files, '*.odin'):
                paths.add(os.path.join(root, file))

    return paths

  def get_file_contents(self, file_path):
    file_view = sublime.active_window().find_open_file(file_path)

    if file_view == None:
      with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()
    else:
      return file_view.substr(sublime.Region(0, file_view.size()))

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

  def make_completion_from_proc_components(self, proc_name, params, return_type, file_name):
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
    completion = [trigger, result]

    # TODO: not sure these are required. they make the results too noisy
    # param completions
    # for param in params:
    #   completion = self.make_completion_from_variable_definition(param, file_name)
    #   completions.append(completion)

    return completion

  def extract_definitions_from_text(self, odin_text):
    defs = self.definition_pattern.findall(odin_text)
    return list(set(defs))

  def make_completion_from_proc_definition(self, definition, file_name):
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

    return self.make_completion_from_proc_components(proc_name, params_list, return_type, file_name)

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
        completions.append(self.make_completion_from_proc_definition(definition, file_name))

    return completions

  # return True (if the next char is empty or a newline) and all the previous chars are valid proc/var name chars up to the '.'
  def is_dot_completion(self, file_view, loc):
    # next char should be some type of space, ie we are not in a word typing
    # next_char = file_view.substr(sublime.Region(loc, loc + 1))
    # if next_char not in ['\n', '', ' ']:
    #   return False

    # walk backwards until we find a '.'. If we hit a non-proc/var char bail out since this isnt a completion
    curr_line_region = file_view.line(loc)
    while loc > curr_line_region.begin():
      char = file_view.substr(sublime.Region(loc - 1, loc))
      if char == '.':
        return True

      if char.isalnum() or char == '_':
        loc -= 1
      else:
        return False

  def extract_includes(self):
    contents = sublime.active_window().active_view().substr(sublime.Region(0, sublime.active_window().active_view().size()))
    self.current_package = self.package_pattern.findall(contents)[0]
    core_packages = self.core_package_pattern.findall(contents)
    shared_packages = self.shared_package_pattern.findall(contents)
    local_packages = self.local_package_pattern.findall(contents)

    for mod in core_packages:
      package = os.path.basename(os.path.normpath(mod[1]))
      alias = mod[0] or package
      self.alias_to_package[alias] = package
      self.included_core_packages.append(package)

    for mod in shared_packages:
      package = os.path.basename(os.path.normpath(mod[1]))
      alias = mod[0] or package
      self.alias_to_package[alias] = package
      self.included_shared_packages.append(package)

    for mod in local_packages:
      # we prefar the last match but if there is no '/' in the path match[1] will be our folder/package
      package = mod[2] or mod[1]
      package = os.path.basename(os.path.normpath(package))
      alias = mod[0] or package
      self.alias_to_package[alias] = package
      self.included_local_packages.append(package)

  def on_activated_async(self, view):
    pass
    # this only works if the code is able to be compiled and we are in a file with main()
    #self.completer.index_file(view.file_name())

  def on_query_completions(self, view, prefix, locations):
    if len(locations) > 1:
      return None

    # cleanup before we start
    self.alias_to_package.clear()
    self.included_core_packages.clear()
    self.included_shared_packages.clear()
    self.included_local_packages.clear()
    self.before_dot = None
    self.search_package = None

    if not self.view_is_odin(view):
      return None

    # dont bother with completions if we are in a comment block or string
    scope_name = view.scope_name(locations[0])
    no_completion_scopes = ['quoted.double', 'quoted.raw', 'comment.line', 'comment.block']
    if any(part in scope_name for part in no_completion_scopes):
      return None

    start_time = time.time()

    # extract the current text. If there is a '.' get the previous word to see if it matches a package
    file_view = sublime.active_window().find_open_file(view.file_name())
    curr_line_region = file_view.line(locations[0])
    curr_line = file_view.substr(curr_line_region).strip()

    # extract the string before the '.' in the current line if there is one and we are on the right side of it typing
    if '.' in curr_line and self.is_dot_completion(file_view, locations[0]):
      pre_cursor_range = file_view.substr(sublime.Region(curr_line_region.begin(), locations[0]))
      space_index = pre_cursor_range.rfind(' ') + 1
      tab_index = pre_cursor_range.rfind('\t') + 1
      start_index = max(space_index, tab_index)
      dot_index = pre_cursor_range.rindex('.')
      self.before_dot = pre_cursor_range[start_index:dot_index]
    else:
      self.before_dot = None

    self.extract_includes()
    paths = self.get_all_odin_file_paths()
    completions = []

    # if we have no . in the text on the current line add the included package names and builtins as completions
    # TODO: add local variables
    if self.before_dot == None:
      for mod in self.included_local_packages:
        alias = self.alias_for_package(mod)
        completions.append(['Package: ' + mod, alias])
        if alias != mod:
          completions.append(['Package: {} (alias for {})'.format(alias, mod), alias])
      for mod in self.included_core_packages:
        alias = self.alias_for_package(mod)
        completions.append(['Package: ' + mod, alias])
        if alias != mod:
          completions.append(['Package: {} (alias for {})'.format(alias, mod), alias])
      for mod in self.included_shared_packages:
        alias = self.alias_for_package(mod)
        completions.append(['Package: ' + mod, alias])
        if alias != mod:
          completions.append(['Package: {} (alias for {})'.format(alias, mod), alias])
      completions.extend(self.built_in_procs)

    # invalidate the cache for our current package
    # TODO: actually cache the completions by package name
    parser.invalidate_completions(self.current_package)

    for path in reversed(list(paths)):
      package_or_filename = self.search_package or os.path.split(path)[1]
      completions += parser.get_completions_from_file(package_or_filename, self.get_file_contents(path))
      # TODO: remove old completions
      # completions += self.get_completions_from_file_path(path)

    # Report time spent building completions before returning
    delta_time_ms = int((time.time() - start_time) * 1000)
    message = 'Odin autocompletion took ' + str(delta_time_ms) + 'ms. Completions: ' + str(len(completions)) + '. Paths: ' + str(len(paths))
    view.window().status_message(message)

    return completions


