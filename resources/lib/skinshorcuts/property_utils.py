# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import ast
import json
import traceback

import xbmcvfs
from .common import log
from .common import read_file
from .common import write_file
from .constants import PROPERTIES_FILE


def read_properties():
    payload = []
    if xbmcvfs.exists(PROPERTIES_FILE):
        # The properties file exists, load from it

        raw_properties = read_file(PROPERTIES_FILE)

        try:
            payload = json.loads(raw_properties)
        except json.decoder.JSONDecodeError:
            payload = ast.literal_eval(raw_properties)
        except:
            payload = []

    return payload


def write_properties(data):
    payload = json.dumps(data, indent=4)
    try:
        write_file(PROPERTIES_FILE, payload)
    except:
        log('Failed to write properties to %s' % PROPERTIES_FILE)
        log(traceback.print_exc())
