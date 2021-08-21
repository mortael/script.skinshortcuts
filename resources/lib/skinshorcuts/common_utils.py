# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from traceback import print_exc

import xbmc
import xbmcgui
from .common import log
from .common import rpc_request


class ShowDialog(xbmcgui.WindowXMLDialog):
    """
    PRETTY SELECT DIALOG
    """

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args)
        self.listing = kwargs.get('listing')
        self.window_title = kwargs.get('window_title')
        self.more = kwargs.get('more')
        self.result = -1
        self.list = None

    def onInit(self):
        try:
            self.list = self.getControl(6)
            self.getControl(3).setVisible(False)
        except:
            log(print_exc())
            self.list = self.getControl(3)

        if self.more is True:
            self.getControl(5).setLabel(xbmc.getLocalizedString(21452))
        else:
            self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(self.window_title)

        # Set Cancel label (Kodi 17+)
        self.getControl(7).setLabel(xbmc.getLocalizedString(222))

        for item in self.listing:
            listitem = xbmcgui.ListItem(label=item.getLabel(), label2=item.getLabel2())
            listitem.setArt({
                'icon': item.getProperty('icon'),
                'thumb': item.getProperty('thumbnail')
            })
            listitem.setProperty('Addon.Summary', item.getLabel2())
            self.list.addItem(listitem)

        self.setFocus(self.list)

    def onAction(self, action):
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448,):
            self.result = -1
            self.close()

    def onClick(self, control_id):
        if control_id == 5:
            self.result = -2
        elif control_id == 6 or control_id == 3:
            num = self.list.getSelectedPosition()
            self.result = num
        else:
            self.result = -1

        self.close()

    def onFocus(self, control_id):
        pass


def rpc_file_get_directory(directory, properties=None):
    if not isinstance(properties, list):
        properties = ["title", "file", "thumbnail"]

    json_payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "Files.GetDirectory",
        "params": {
            "properties": properties,
            "directory": "%s" % directory,
            "media": "files"
        }
    }
    return rpc_request(json_payload)
