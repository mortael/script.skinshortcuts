# -*- coding: utf-8 -*-

import os

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')

KODI_VERSION = xbmc.getInfoLabel("System.BuildVersion").split(".")[0]

CWD = ADDON.getAddonInfo('path')

DEFAULT_PATH = xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'shortcuts'))
DATA_PATH = xbmcvfs.translatePath("special://profile/addon_data/%s" % ADDON_ID)
SKIN_PATH = xbmcvfs.translatePath("special://skin/shortcuts/")
RESOURCE_PATH = xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'lib'))
MASTER_PATH = xbmcvfs.translatePath("special://masterprofile/addon_data/%s" % ADDON_ID)

LANGUAGE = ADDON.getLocalizedString
