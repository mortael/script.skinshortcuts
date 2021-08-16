# -*- coding: utf-8 -*-

import hashlib
import sys
import traceback

import xbmc
from .constants import ADDON
from .constants import ADDON_ID

PY2 = sys.version_info.major == 2


# noinspection PyUnresolvedReferences
def log(txt):
    if ADDON.getSetting("enable_logging") == "true":
        if isinstance(txt, bytes):
            txt = txt.decode('utf-8')
        elif PY2 and isinstance(txt, unicode):
            txt = txt.encode('utf-8')

        message = '%s: %s' % (ADDON_ID, txt)
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def get_hash(filename):
    try:
        md5 = hashlib.md5()
        with open(filename, 'r') as file_handle:
            file_contents = file_handle.read()
            md5.update(file_contents.encode('utf-8'))
    except:
        log("Unable to generate hash for %s" % filename)
        traceback.print_exc()
        raise
