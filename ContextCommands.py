import sublime
import sublime_plugin
import os
import shutil
import threading


class AdaCaseSelectionCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()
		regions_by_line = self.view.split_by_newlines(sel[0])

		for region in regions_by_line:
			txt = self.view.substr(region)
			new_txt = ''
			print('--- before: ' + txt)
			txt = txt.lower()
			upper_next = True
			lower_next = False
			for i in range(0, len(txt)):
				if txt[i] == '_':
					upper_next = True
					lower_next = False
					new_txt += txt[i]
					continue
				elif txt[i].isalnum():
					if upper_next:
						new_txt += txt[i].upper()
					elif lower_next:
						new_txt += txt[i].lower()
					upper_next = False
					lower_next = True
				else:
					new_txt += txt[i]
			self.view.replace(edit, region, new_txt)

