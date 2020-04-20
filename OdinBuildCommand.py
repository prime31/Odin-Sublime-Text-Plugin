import sublime
import sublime_plugin
import os
import shutil
import subprocess as subp

from Odin import odin_set_vc_vars

SENTINEL="SUBL_VC_VARS"

class OdinBuildCommand(sublime_plugin.WindowCommand):
	def run(self, metal=False, d3d11=False, opt_level=0, print_args=False, apitrace=False):
		if sublime.platform() == 'windows':
			self.build_win(d3d11, opt_level)
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

		if print_args:
			print(args)

		if apitrace:
			args.pop()
			args.append('apitrace trace --api gl ./' + vars['file_base_name'])
			self.window.active_view().window().run_command('exec', {
				'shell': True,
				'shell_cmd': ' '.join(args),
				'quiet': True,
				'working_dir' : vars['file_path'],
				'file_regex': '^(.*?)\((\d+):(\d+)\)\s(.*?)$',
				'syntax': 'BuildOutput.sublime-syntax'
			})
			return

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
	
	def build_win(self, d3d11=False, opt_level=0):
		odin_set_vc_vars.set()
		vars = self.window.extract_variables()
		dir_path = os.path.dirname(os.path.realpath(__file__))
		bat_path = os.path.join(dir_path, 'build_windows.bat')

		args = ['"' + bat_path + '"', vars['file_base_name']]

		build_opt = '"-opt=' + str(opt_level) + ' -keep-temp-files"'
		if d3d11:
			build_opt += ' -define:D3D11=1'
		args.append(build_opt)

		# get all our dll paths
		native_libs = self.get_all_native_paths('.lib', True)
		native_libs = map(lambda path: path.replace('/', '\\'), native_libs)

		filter_lib = 'sokol_gl' if d3d11 else 'sokol_d3d11'
		native_libs = list(filter(lambda path: filter_lib not in path, native_libs))

		if not d3d11:
			native_libs.append('opengl32.lib')
		native_libs.append('MSVCRTD.lib')
		args.append('"' + ' '.join(native_libs) + '"')

		# shove all our dll paths in the PATH environment var, being careful not to dupe them
		native_dlls = list(map(lambda path: path.replace('/', '\\'), self.get_all_native_paths('.dll', False)))
		env_path = os.environ['PATH']
		native_dlls = [path for path in native_dlls if path not in env_path]

		# print('native_libs', native_libs)
		# print('native_dlls', native_dlls)

		if len(native_dlls) > 0:
			os.environ['PATH'] = os.environ['PATH'] + ';' + ';'.join(native_dlls)

		self.window.active_view().window().run_command('exec', {
			'shell': True,
			'shell_cmd': ' '.join(args),
			'quiet': False,
			'working_dir' : vars['file_path'],
			'file_regex': '^(.*?)\((\d+):(\d+)\)\s(.*?)$',
			'syntax': 'BuildOutput.sublime-syntax'
		})

	# fetches all the paths that have dylibs/dlls in them in folders named 'native' in the 'odin/shared' folder
	def get_all_native_paths(self, lib_ext='.dylib', append_lib_name=False):
		native_dirs = []
		odin_path = os.path.expanduser(self.window.active_view().settings().get('odin_install_path', '~/odin'))
		odin_shared_path = os.path.join(odin_path, 'shared')
		for root, dirs, files in os.walk(odin_shared_path):
			dirs[:] = list(filter(lambda x: not x == '.git', dirs))
			if root.endswith('native'):
				for f in files:
					if f.endswith(lib_ext):
						if append_lib_name:
							native_dirs.append(os.path.join(root, f))
						else:
							native_dirs.append(root)
		return native_dirs

