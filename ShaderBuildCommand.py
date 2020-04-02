import sublime
import sublime_plugin
import os
import shutil
import subprocess as subp

class ShaderBuildCommand(sublime_plugin.WindowCommand):
	def run(self):
		self.window.active_view().window().run_command('build_shader', {'paths': [self.window.active_view().file_name()]})