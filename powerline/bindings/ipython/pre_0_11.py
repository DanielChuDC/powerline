# vim:fileencoding=utf-8:noet

import re

from weakref import ref

from powerline.ipython import IPythonPowerline, RewriteResult
from powerline.lib.unicode import string

from IPython.Prompts import BasePrompt
from IPython.ipapi import get as get_ipython
from IPython.ipapi import TryNext


class IPythonInfo(object):
	def __init__(self, cache):
		self._cache = cache

	@property
	def prompt_count(self):
		return self._cache.prompt_count


class PowerlinePrompt(BasePrompt):
	def __init__(self, powerline, powerline_last_in, old_prompt):
		self.powerline_last_in = powerline_last_in
		self.powerline_segment_info = IPythonInfo(old_prompt.cache)
		self.cache = old_prompt.cache
		if hasattr(old_prompt, 'sep'):
			self.sep = old_prompt.sep
		self.pad_left = False

	def __str__(self):
		self.set_p_str()
		return string(self.p_str)

	def set_p_str(self):
		self.p_str, self.p_str_nocolor, self.powerline_prompt_width = (
			self.powerline.render(
				is_prompt=self.powerline_is_prompt,
				side='left',
				output_raw=True,
				output_width=True,
				segment_info=self.powerline_segment_info,
				matcher_info=self.powerline_prompt_type,
			)
		)

	@staticmethod
	def set_colors():
		pass


class PowerlinePrompt1(PowerlinePrompt):
	powerline_prompt_type = 'in'
	powerline_is_prompt = True
	rspace = re.compile(r'(\s*)$')

	def __str__(self):
		self.cache.prompt_count += 1
		self.set_p_str()
		self.cache.last_prompt = self.p_str_nocolor.split('\n')[-1]
		return string(self.p_str)

	def set_p_str(self):
		super(PowerlinePrompt1, self).set_p_str()
		self.nrspaces = len(self.rspace.search(self.p_str_nocolor).group())
		self.powerline_last_in['nrspaces'] = self.nrspaces

	def auto_rewrite(self):
		return RewriteResult(self.powerline.render(
			is_prompt=False,
			side='left',
			matcher_info='rewrite',
			segment_info=self.powerline_segment_info) + (' ' * self.nrspaces)
		)


class PowerlinePromptOut(PowerlinePrompt):
	powerline_prompt_type = 'out'
	powerline_is_prompt = False

	def set_p_str(self):
		super(PowerlinePromptOut, self).set_p_str()
		spaces = ' ' * self.powerline_last_in['nrspaces']
		self.p_str += spaces
		self.p_str_nocolor += spaces


class PowerlinePrompt2(PowerlinePromptOut):
	powerline_prompt_type = 'in2'
	powerline_is_prompt = True


class ConfigurableIPythonPowerline(IPythonPowerline):
	def init(self, config_overrides=None, theme_overrides={}, paths=None):
		self.config_overrides = config_overrides
		self.theme_overrides = theme_overrides
		self.paths = paths
		super(ConfigurableIPythonPowerline, self).init()

	def do_setup(self, wrefs):
		for wref in wrefs:
			obj = wref()
			if obj is not None:
				setattr(obj, 'powerline', self)


def setup(**kwargs):
	ip = get_ipython()

	old_widths = {}
	powerline = ConfigurableIPythonPowerline(**kwargs)

	def late_startup_hook():
		last_in = {'nrspaces': 0}
		prompts = []
		for attr, prompt_class in (
			('prompt1', PowerlinePrompt1),
			('prompt2', PowerlinePrompt2),
			('prompt_out', PowerlinePromptOut)
		):
			old_prompt = getattr(ip.IP.outputcache, attr)
			prompt = prompt_class(powerline, last_in, old_prompt)
			setattr(ip.IP.outputcache, attr, prompt)
			prompts.append(ref(prompt))
		powerline.setup(prompts)
		raise TryNext()

	def shutdown_hook():
		powerline.shutdown()
		raise TryNext()

	ip.IP.hooks.late_startup_hook.add(late_startup_hook)
	ip.IP.hooks.shutdown_hook.add(shutdown_hook)
