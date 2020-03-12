import sublime
import sublime_plugin
import os
import shutil
import threading

from functools import partial


class CommandHelper(object):
	@staticmethod
	def get_path(cmd, paths):
		try:
			return paths[0]
		except IndexError:
			return cmd.window.active_view().file_name()

	@staticmethod
	def copy_to_clipboard(cmd, data):
		sublime.set_clipboard(data)
		lines = len(data.split('\n'))
		cmd.window.status_message('Copied {} to clipboard'.format(
				'{} lines'.format(lines) if lines > 1 else '"{}"'.format(data)
		))



class CloneRightCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("create_pane",        {"direction": "right"})
        self.window.run_command("clone_file_to_pane", {"direction": "right"})


class OpenInFinderCommand(sublime_plugin.WindowCommand):
	def run(self, paths):
		path = CommandHelper.get_path(self, paths)

		# ensure we have a folder and not a file
		if os.path.isfile(path):
			path = os.path.split(os.path.abspath(path))[0]

		self.window.run_command("exec", {
			"cmd": ["open", path],
			"shell": False
			})


class OpenInTerminalCommand(sublime_plugin.WindowCommand):
	def run(self, paths):
		path = CommandHelper.get_path(self, paths)

		# ensure we have a folder and not a file
		if os.path.isfile(path):
			path = os.path.split(os.path.abspath(path))[0]

		self.window.run_command("exec", {
			"cmd": ["open", "-a", "Terminal", path],
			"shell": False
			})


class DuplicateCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		source = CommandHelper.get_path(self, paths)
		base, leaf = os.path.split(source)

		name, ext = os.path.splitext(leaf)
		if ext is not '':
			while '.' in name:
				name, _ext = os.path.splitext(name)
				ext = _ext + ext
				if _ext is '':
					break

		input_panel = self.window.show_input_panel('Duplicate as:', source, partial(self.on_done, source, base), None, None)
		input_panel.sel().clear()
		input_panel.sel().add(sublime.Region(len(base) + 1, len(source) - len(ext)))

	def on_done(self, source, base, new):
		new = os.path.join(base, new)
		threading.Thread(target = self.copy, args = (source, new)).start()

	def copy(self, source, new):
		self.window.status_message('Copying "{}" to "{}"'.format(source, new))

		try:
			base = os.path.dirname(new)
			if not os.path.exists(base):
				os.makedirs(base)

			if os.path.isdir(source):
				shutil.copytree(source, new)
			else:
				shutil.copy2(source, new)
				self.window.open_file(new)

		except OSError as error:
			self.window.status_message('Unable to duplicate: "{}" to "{}". {error}'.format(source, new, error))
		except:
			self.window.status_message('Unable to duplicate: "{}" to "{}"'.format(source, new))

		self.window.run_command('refresh_folder_list')

	def description(self):
		return 'Duplicate…'


class MoveCommand(sublime_plugin.WindowCommand):
  def run(self, paths):
    source = CommandHelper.get_path(self, paths)
    base, leaf = os.path.split(source)
    _, ext = os.path.splitext(leaf)

    input_panel = self.window.show_input_panel('Move to:', source, partial(self.on_done, source), None, None)
    input_panel.sel().clear()
    input_panel.sel().add(sublime.Region(len(base) + 1, len(source) - len(ext)))

  def on_done(self, source, new):
    threading.Thread(target = self.move, args = (source, new)).start()

  def move(self, source, new):
    self.window.status_message('Moving "{}" to "{}"'.format(source, new))

    try:
      base = os.path.dirname(new)
      if not os.path.exists(base):
        os.makedirs(base)

      shutil.move(source, new)

      if os.path.isfile(new):
        self.retarget_view(source, new)
      else:
        self.retarget_all_views(source, new)

    except OSError as error:
      self.window.status_message('Unable to moving: "{}" to "{}". {}'.format(source, new, error))
    except:
      self.window.status_message('Unable to moving: "{}" to "{}"'.format(source, new))

    self.window.run_command('refresh_folder_list')

  def description(self):
    return 'Move…'