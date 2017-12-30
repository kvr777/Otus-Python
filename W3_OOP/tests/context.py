# -*- coding: utf-8 -*-

import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(root_dir, 'api_handler'))

import api, store, scoring_new
