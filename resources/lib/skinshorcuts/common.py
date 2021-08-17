# -*- coding: utf-8 -*-

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


def get_hash(filename):
    try:
        md5 = hashlib.md5()
        with open(filename, 'rb') as file_handle:
            file_contents = file_handle.read()
        md5.update(file_contents)
        return md5.hexdigest()
    except:
        log("Unable to generate hash for %s" % filename)
        traceback.print_exc()
        raise
