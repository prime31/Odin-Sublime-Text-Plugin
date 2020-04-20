import sublime
import sublime_plugin

from threading import Thread
from subprocess import Popen, PIPE
from os import environ

SENTINEL="SUBL_VC_VARS"

def _get_vc_env():
	"""
	Run the batch file specified in the vc_vars_path setting
	and return back a dictionary of the environment that the batch file sets up.

	Returns None if the preference is missing or the batch file fails.
	"""
	settings = sublime.load_settings("Preferences.sublime-settings")
	vars_cmd = settings.get("vc_vars_path")
	"""vars_arch = settings.get("vc_vars_arch", "amd64")"""

	if vars_cmd is None:
		print("set_vc_vars: Cannot set Visual Studio Environment")
		print("set_vc_vars: Add 'vc_vars_path' setting to settings and restart")
		return None

	try:
		# Run the batch, outputting a sentinel value so we can separate out
		# any error messages the batch might generate.
		shell_cmd = "\"{0}\" {1} && echo {2} && set".format(
			vars_cmd, "x64", SENTINEL)

		output = Popen(shell_cmd, stdout=PIPE, shell=True).stdout.read()

		lines = [line.strip() for line in output.decode("utf-8").splitlines()]
		env_lines = lines[lines.index(SENTINEL) + 1:]
	except:
		return None

	# Convert from var=value to dictionary key/value pairs. We upper case the
	# keys, since Python does that to the mapping it stores in environ.
	env = {}
	for env_var in env_lines:
		parts = env_var.split("=", maxsplit=1)
		env[parts[0].upper()] = parts[1]

	return env

def install_vc_env():
	"""
	Try to collect the appropriate Visual Studio environment variables and
	set them into the current environment.
	"""
	vc_env = _get_vc_env()
	if vc_env is None:
		print("set_vc_vars: Unable to fetch the Visual Studio Environment")
		return sublime.status_message("Error fetching VS Environment")

	# Add newly set environment variables
	for key in vc_env.keys():
		if key not in environ:
			environ[key] = vc_env[key]

	# Update existing variables whose values changed.
	for key in environ:
		if key in vc_env and environ[key] != vc_env[key]:
			environ[key] = vc_env[key]

	# Set a sentinel variable so we know not to try setting up the path again.
	environ[SENTINEL] = "BOOTSTRAPPED"
	sublime.status_message("VS Environment enabled")

def set():
	if sublime.platform() != "windows":
		return

	# To reload the environment if it changes, restart Sublime.
	if SENTINEL in environ:
		return sublime.status_message("VS Environment already enabled")

	# Update in the background so we don't block the UI
	#Thread(target=install_vc_env).start()
	install_vc_env()

