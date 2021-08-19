# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import hashlib
import json
import os
import traceback

import xbmc
from .constants import ADDON
from .constants import ADDON_ID


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
    if not os.path.isfile(filename):
        return None

    try:
        md5 = hashlib.md5()
        file_contents = read_file(filename, 'rb')
        md5.update(file_contents)
        return md5.hexdigest()
    except:
        log("Unable to generate hash for %s" % filename)
        traceback.print_exc()
        raise


def rpc_request(request):
    payload = xbmc.executeJSONRPC(json.dumps(request))
    response = json.loads(payload)
    log('JSONRPC: Requested |%s| received |%s|' % (request, str(response)))
    return response


def validate_rpc_response(request, response):
    if 'result' in response:
        return True

    if 'error' in response:
        message = response['error']['message']
        code = response['error']['code']
        error = 'JSONRPC: Requested |%s| received error |%s| and code: |%s|' % \
                (request, message, code)
    else:
        error = 'JSONRPC: Requested |%s| received error |%s|' % (request, str(response))

    log(error)
    return False


def toggle_debug_logging(enable=False):
    # return None on error
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "Settings.getSettings"
    }

    response = rpc_request(payload)
    if not validate_rpc_response(payload, response):
        return None

    logging_enabled = True
    if 'settings' in response['result'] and response['result']['settings'] is not None:
        for item in response['result']['settings']:
            if item['id'] == 'debug.showloginfo':
                logging_enabled = item['value'] is True
                break

    if (not enable and logging_enabled) or (enable and not logging_enabled):
        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "Settings.setSettingValue",
            "params": {
                "setting": "debug.showloginfo",
                "value": enable is True
            }
        }

        response = rpc_request(payload)
        if not validate_rpc_response(payload, response):
            return None

        logging_enabled = not logging_enabled

    return logging_enabled == enable
