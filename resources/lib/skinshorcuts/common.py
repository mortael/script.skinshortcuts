# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import hashlib
import traceback

import xbmc
from .constants import ADDON
from .constants import ADDON_ID


# noinspection PyUnresolvedReferences
def log(txt):
    if ADDON.getSetting("enable_logging") == "true":
        if isinstance(txt, bytes):
            txt = txt.decode('utf-8')

        message = '%s: %s' % (ADDON_ID, txt)
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def read_file(filename, mode='r'):
    with open(filename, mode) as file_handle:
        return file_handle.read()


def write_file(filename, contents, mode='w'):
    with open(filename, mode) as file_handle:
        file_handle.write(contents)


def get_hash(filename):
    try:
        md5 = hashlib.md5()
        file_contents = read_file(filename, 'rb')
        md5.update(file_contents)
        return md5.hexdigest()
    except:
        log("Unable to generate hash for %s" % filename)
        traceback.print_exc()
        raise
