import sublime
import sublime_plugin
import os
import shutil
import threading
import re


def to_ada_case(txt):
	new_txt = ''

	orig_txt = txt
	txt = txt.lower()
	upper_next = True
	lower_next = False
	for i in range(0, len(txt)):
		if txt[i] == '_':
			upper_next = True
			lower_next = False
			new_txt += txt[i]
			continue
		elif i > 0 and orig_txt[i].isupper():
			upper_next = False
			new_txt += '_' + orig_txt[i]
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
	return new_txt


class AdaCaseSelectionCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()
		regions_by_line = self.view.split_by_newlines(sel[0])

		for region in regions_by_line:
			txt = self.view.substr(region)
			new_txt = ''

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


class ToUpperSelectionCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()
		for selection in sel:
			regions_by_line = self.view.split_by_newlines(selection)

			for region in regions_by_line:
				txt = self.view.substr(region)
				self.view.replace(edit, region, txt.upper())


class ToLowerSelectionCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()
		for selection in sel:
			regions_by_line = self.view.split_by_newlines(selection)

			for region in regions_by_line:
				txt = self.view.substr(region)
				self.view.replace(edit, region, txt.lower())


class VToOdinStructCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		new_txt = ''
		regions_to_kill = []
		regions_by_line = self.view.split_by_newlines(self.view.sel()[0])
		for region in regions_by_line:
			txt = self.view.substr(region)
			if any(piece in txt for piece in ['struct']):
				x = re.findall(r'.*?struct\s(\w+)\s', txt)
				new_txt += to_ada_case(x[0]) + ' :: struct {\n'
			elif txt.find(':') > 0:
				regions_to_kill.append(region)
			elif txt.find('}') >= 0:
				new_txt += '}\n'
			else:
				tmp = re.findall(r'\s*(\w+)\s+([\w\[\]]+).*$', txt)
				name = tmp[0][0]
				typ = 'i32' if tmp[0][1] == 'int' else tmp[0][1]
				new_txt += '\t' + name + ': ' + typ + ',\n'

		self.view.replace(edit, self.view.sel()[0], new_txt)

