import sublime
import sublime_plugin


class OpenInFinderCommand(sublime_plugin.WindowCommand):
	def run(self, files):
		self.window.run_command("exec", {
			"cmd": ["open", files[0]],
			"shell": False
			})

	# Make command visible only when there is a single file
	def is_visible(self, files):
		return len(files) == 1