import sublime
import sublime_plugin
import os
import re
import shutil
import platform
import threading
import subprocess

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

	def is_enabled(self):
		return platform.system() == 'Darwin'


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

	def is_enabled(self):
		return platform.system() == 'Darwin'


class BuildShadersCommand(sublime_plugin.WindowCommand):
	@staticmethod
	def do_build(window, file_or_folder):
		file_param = '"*.fx"' if os.path.isdir(file_or_folder) else os.path.basename(file_or_folder)
		root = file_or_folder if os.path.isdir(file_or_folder) else os.path.dirname(file_or_folder)
		print(file_param, root)

		results = ['<body style="border: 4px solid white; padding: 10px;"><h2>Shader Build Report</h2>']

		try:
			script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'buildEffect.sh')
			output = subprocess.check_output(['"' + script_path + '" ' + '"' + root + '" ' + file_param], shell=True, stderr=subprocess.STDOUT, cwd=root)

			# print the raw output to the console
			print(output)
			output = output.decode('utf-8').split('\r\n')
			output = list(filter(lambda l: not any(ele in l for ele in ['Microsoft']), output))
			output = [l for l in output if len(l) > 2] # kill all empty and \n lines

			# format the output
			match_path_pattern = re.compile(r'.*?([a-zA-Z]:\\.*?(\w*\.fx))')
			for i, s in enumerate(output):
				# strip long path names
				matches = match_path_pattern.findall(s)
				for m in matches:
					output[i] = output[i].replace(m[0], m[1])

				output[i] = output[i].replace('compilation failed;', '<b style="color: red">compilation failed:</b>')
				output[i] = output[i].replace('compilation succeeded; see', '<b style="color: green">compilation succeeded:</b>')

				if 'no code produced' in s:
					output[i] += '<br>'

				if 'error' in s:
					output[i] = '<b style="color: red;">' + output[i] + '</b>'

			print(output)
			out = '<br>'.join(output)
			results.append(out.replace('\n', '<br>'))
			results.append('</body>')
		except subprocess.CalledProcessError as e:
			raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))

		window.active_view().show_popup('<br>'.join(results), max_width=1024, max_height=768)

	def run(self, paths):
		self.do_build(self.window, paths[0])

	def is_visible(self, paths):
		return platform.system() == 'Darwin'

	def is_enabled(self, paths):
		return len(paths) == 1 and os.path.isdir(paths[0])


class BuildShaderCommand(BuildShadersCommand):
	def run(self, paths):
		self.do_build(self.window, paths[0])

	def is_visible(self, paths):
		return platform.system() == 'Darwin'

	def is_enabled(self, paths):
		return len(paths) == 1 and os.path.isfile(paths[0])


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