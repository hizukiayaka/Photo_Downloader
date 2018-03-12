#!/usr/bin/env python

import yaml

def read_config(config_path='config.yaml'):
	try:
		with open(config_path, 'r') as config_file:

			config = yaml.load(config_file)
			return config
	except IOError:
		return None
