import sublime
import sublime_plugin
import re
import os
import platform
import glob
import fnmatch
import time
from Odin import parser


class OdinCompletions(sublime_plugin.EventListener):
  full_reindex_interval_secs = 60 * 10 # Ten minutes
  last_full_reindex_secs = -full_reindex_interval_secs
  alias_to_package = dict()

  package_pattern = re.compile(r'package\s+(.*)')
  core_package_pattern = re.compile(r'import\s(\w+|)\s*\"(?:core:)+(.*?)\"')
  shared_package_pattern = re.compile(r'import\s(\w+|)\s*\"(?:shared:)+(.*?)\"')
  local_package_pattern = re.compile(r'import\s(\w+|)\s*\"(?!.*?:)(\w+)+(.*?)\"')

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

  def add_import(self, view, package):
    sublime.active_window().run_command('insert_import', {'package': package})

  def get_all_odin_file_paths(self, view):
    odin_path = os.path.expanduser(view.settings().get('odin_install_path', '~/odin'))
    paths = set()
    window = sublime.active_window()

    word_before_dot = self.alias_to_package[self.before_dot] if self.before_dot in self.alias_to_package else self.before_dot

    # use this data to filter so we dont pile on unecessary files to parse
    is_core_package_completion = word_before_dot in self.included_core_packages
    is_shared_package_completion = word_before_dot in self.included_shared_packages
    is_local_package_completion = word_before_dot in self.included_local_packages
    is_var_field_access = word_before_dot != None and not is_core_package_completion and not is_local_package_completion and not is_shared_package_completion

    # if we have a word before the dot and is_var_field_access = True this could potentially be a package
    # name that we can add an auto-import for
    if word_before_dot != None and is_var_field_access and word_before_dot in parser.package_to_path:
      view.show_popup_menu(['Add import   ' + parser.package_to_path[word_before_dot]], lambda index: self.add_import(view, parser.package_to_path[word_before_dot]) if index >= 0 else None)

    if word_before_dot == None and not is_var_field_access:
      paths.add(os.path.join(odin_path, 'core/builtin/builtin.odin'))

      # self.current_package is where we will source our files from
      current_folder = os.path.dirname(sublime.active_window().active_view().file_name())
      for file in glob.glob(current_folder + '/*.odin'):
        paths.add(file)


    if is_local_package_completion and not is_var_field_access:
      self.search_package = word_before_dot
      if len(self.included_local_packages) > 0:
        curr_path = os.path.dirname(sublime.active_window().active_view().file_name())
        for root, dirs, files in os.walk(curr_path):
          dirs[:] = list(filter(lambda x: not x == '.git', dirs))
          root_dir = os.path.basename(root)
          if root_dir == word_before_dot and root_dir in self.included_local_packages:
            for file in fnmatch.filter(files, '*.odin'):
              paths.add(os.path.join(root, file))

    if is_shared_package_completion and not is_var_field_access:
      self.search_package = word_before_dot
      # include any imported shared packages
      if len(self.included_shared_packages) > 0:
        odin_shared_path = os.path.join(odin_path, 'shared')
        for root, dirs, files in os.walk(odin_shared_path):
          dirs[:] = list(filter(lambda x: not x == '.git', dirs))
          root_dir = os.path.basename(root)
          if root_dir == word_before_dot and root_dir in self.included_shared_packages:
            for file in fnmatch.filter(files, '*.odin'):
              paths.add(os.path.join(root, file))

    if is_core_package_completion and not is_var_field_access:
      self.search_package = word_before_dot
      # include any imported core packages
      if len(self.included_core_packages) > 0:
        odin_lib_path = os.path.join(odin_path, 'core')
        for root, dirs, files in os.walk(odin_lib_path):
          root_dir = os.path.basename(root)
          if root_dir == word_before_dot and root_dir in self.included_core_packages:
            # special care for os
            if root_dir == 'os':
              paths.add(os.path.join(root, 'os.odin'))
              paths.add(os.path.join(root, 'os_' + platform.system().lower() + '.odin'))
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

  # return True if all the previous chars are valid (a-zA-Z0-9_) up to the '.'
  def get_prefix_before_dot(self, file_view, loc):
    # next char should be some type of space, paren or non-word
    next_char = file_view.substr(sublime.Region(loc, loc + 1))
    if next_char.isalnum():
      return False

    # walk backwards until we find a '.'. If we hit a non-char (a-zA-Z0-9_) bail out since this isnt a completion
    curr_line_region = file_view.line(loc)

    def get_before_dot(dot_loc):
      region_end = dot_loc
      while dot_loc > curr_line_region.begin():
        prev_char = file_view.substr(sublime.Region(dot_loc - 1, dot_loc))
        if prev_char.isalnum() or prev_char == '_':
          dot_loc -= 1
        else:
          return file_view.substr(sublime.Region(dot_loc, region_end))
      return None

    while loc > curr_line_region.begin():
      char = file_view.substr(sublime.Region(loc - 1, loc))
      if char == '.':
        return get_before_dot(loc - 1)

      if char.isalnum() or char == '_':
        loc -= 1
      else:
        return None
    return None

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

  def on_post_save_async(self, view):
    if time.time() - self.last_full_reindex_secs > self.full_reindex_interval_secs:
      parser.reindex_all_package_names(view, os.path.dirname(sublime.active_window().active_view().file_name()))
      self.last_full_reindex_secs = time.time()

  def on_query_completions(self, view, prefix, locations):
    if len(locations) > 1 or not view.file_name().endswith('.odin'):
      return None

    # cleanup before we start
    self.alias_to_package.clear()
    self.included_core_packages.clear()
    self.included_shared_packages.clear()
    self.included_local_packages.clear()
    self.before_dot = None
    self.search_package = None

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
    self.before_dot = self.get_prefix_before_dot(file_view, locations[0])

    self.extract_includes()
    paths = self.get_all_odin_file_paths(view)
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

    # Report time spent building completions before returning
    delta_time_ms = int((time.time() - start_time) * 1000)
    message = 'Odin autocompletion took ' + str(delta_time_ms) + 'ms. Completions: ' + str(len(completions)) + '. Paths: ' + str(len(paths))
    view.window().status_message(message)

    return completions


