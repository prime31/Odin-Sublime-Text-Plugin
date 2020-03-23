import sublime
import sublime_plugin
import os
import shutil
import subprocess as subp

class OdinBuildCommand(sublime_plugin.WindowCommand):
	def run(self, metal=False, opt_level=0):
		if os.name == 'nt':
			self.build_win(opt_level)
			return

		vars = self.window.extract_variables()
		args = ['odin', 'build', vars['file'], '-opt=' + str(opt_level)]
		if metal:
			args.append('-define:METAL=1')

		# we use the native_dirs to make a DYLD_LIBRARY_PATH
		native_dirs = self.get_all_native_paths()

		# build up a run command to happen after the build command
		lib_path = '.:' + ':'.join(native_dirs)
		os.environ['DYLD_LIBRARY_PATH'] = lib_path

		exe_exists = '[ -f ' + os.path.join(vars['file_path'], vars['file_base_name']) + ' ]'
		args.extend(['&&', 'export', 'DYLD_LIBRARY_PATH=' + lib_path + ';', exe_exists, '&&', './' + vars['file_base_name']])

		# kill the old exe so that we fail to run anything if we dont build
		if os.path.exists(vars['file_base_name']):
			os.remove(vars['file_base_name'])

		self.window.active_view().window().run_command('exec', {
			'shell': True,
			'shell_cmd': ' '.join(args),
			'quiet': True,
			'working_dir' : vars['file_path'],
			'file_regex': '^(.*?)\((\d+):(\d+)\)\s(.*?)$',
			'syntax': 'BuildOutput.sublime-syntax'
		})
	
	def build_win(self, opt_level=0):
		vars = self.window.extract_variables()
		dir_path = os.path.dirname(os.path.realpath(__file__))
		bat_path = os.path.join(dir_path, 'build_windows.bat')

		args = ['"' + bat_path + '"', vars['file_base_name']]

		# get all our dll paths
		native_dirs = self.get_all_native_paths('.dll')

		# shove all our dll paths in the PATH environment var
		os.environ['PATH'] = os.environ['PATH'] + ';' + ';'.join(native_dirs)

		self.window.active_view().window().run_command('exec', {
			'shell': True,
			'shell_cmd': ' '.join(args),
			'quiet': False,
			'working_dir' : vars['file_path'],
			'file_regex': '^(.*?)\((\d+):(\d+)\)\s(.*?)$',
			'syntax': 'BuildOutput.sublime-syntax'
		})

	# fetches all the paths that have dylibs/dlls in them in folders named 'native' in the 'odin/shared' folder
	def get_all_native_paths(self, lib_ext='.dylib'):
		native_dirs = []
		odin_shared_path = os.path.expanduser('~/odin/shared')
		for root, dirs, files in os.walk(odin_shared_path):
			dirs[:] = list(filter(lambda x: not x == '.git', dirs))
			if root.endswith('native'):
				if any(lib_ext in f for f in files):
					native_dirs.append(root)
		return native_dirs

