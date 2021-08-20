# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

# noinspection PyCompatibility
import _thread as thread
import calendar
import os
import sys
from time import gmtime
from time import strftime
from traceback import print_exc
# noinspection PyCompatibility
from urllib.parse import parse_qsl
# noinspection PyCompatibility
from urllib.parse import unquote

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs
from . import datafunctions
from . import library
from . import nodefunctions
from . import xmlfunctions
from .common import log
from .common import rpc_request
from .constants import ADDON
from .constants import ADDON_NAME
from .constants import ADDON_VERSION
from .constants import CWD
from .constants import DATA_PATH
from .constants import HOME_WINDOW
from .constants import LANGUAGE
from .constants import MASTER_PATH
from .constants import SKIN_DIR


class Main:
    # MAIN ENTRY POINT
    def __init__(self):
        self._parse_argv()

        self.data_func = datafunctions.DataFunctions()
        self.node_func = nodefunctions.NodeFunctions()
        self.xml_func = xmlfunctions.XMLFunctions()
        self.lib_func = library.LibraryFunctions()

        # Create data and master paths if not exists
        if not xbmcvfs.exists(DATA_PATH):
            xbmcvfs.mkdir(DATA_PATH)
        if not xbmcvfs.exists(MASTER_PATH):
            xbmcvfs.mkdir(MASTER_PATH)

        # Perform action specified by user
        if not self.TYPE:
            line1 = "This addon is for skin developers, and requires skin support"
            xbmcgui.Dialog().ok(ADDON_NAME, line1)

        if self.TYPE == "buildxml":
            xbmc.sleep(100)
            self.xml_func.build_menu(self.MENUID, self.GROUP, self.LEVELS, self.MODE,
                                     self.OPTIONS, self.MINITEMS)

        if self.TYPE == "launch":
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False,
                                      listitem=xbmcgui.ListItem())
            self._launch_shortcut()
        if self.TYPE == "launchpvr":
            json_payload = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "Player.Open",
                "params": {
                    "item": {
                        "channelid": "%s" % self.CHANNEL
                    }
                }
            }
            _ = rpc_request(json_payload)
        if self.TYPE == "manage":
            self._manage_shortcuts(self.GROUP, self.DEFAULTGROUP, self.NOLABELS, self.GROUPNAME)

        if self.TYPE == "hidesubmenu":
            self._hidesubmenu(self.MENUID)
        if self.TYPE == "resetlist":
            self._resetlist(self.MENUID, self.NEXTACTION)

        if self.TYPE == "shortcuts":
            # We're just going to choose a shortcut, and save its details to the given
            # skin labels

            # Load library shortcuts in thread
            thread.start_new_thread(self.lib_func.load_all_library, ())

            if self.GROUPING is not None:
                selectedShortcut = self.lib_func.select_shortcut(
                    "", grouping=self.GROUPING,
                    custom=self.CUSTOM, showNone=self.NONE
                )
            else:
                selectedShortcut = self.lib_func.select_shortcut("", custom=self.CUSTOM,
                                                                 showNone=self.NONE)

            # Now set the skin strings
            if selectedShortcut is not None and selectedShortcut.getProperty("Path"):
                path = selectedShortcut.getProperty("Path")

                if selectedShortcut.getProperty("chosenPath"):
                    path = selectedShortcut.getProperty("chosenPath")

                if path.startswith("pvr-channel://"):
                    path = "RunScript(script.skinshortcuts,type=launchpvr&channel=" + \
                           path.replace("pvr-channel://", "") + ")"
                if self.LABEL is not None and selectedShortcut.getLabel() != "":
                    xbmc.executebuiltin("Skin.SetString(" + self.LABEL + "," +
                                        selectedShortcut.getLabel() + ")")
                if self.ACTION is not None:
                    xbmc.executebuiltin("Skin.SetString(" + self.ACTION + "," + path + " )")
                if self.SHORTCUTTYPE is not None:
                    xbmc.executebuiltin("Skin.SetString(" + self.SHORTCUTTYPE + "," +
                                        selectedShortcut.getLabel2() + ")")
                if self.THUMBNAIL is not None and selectedShortcut.getProperty("icon"):
                    xbmc.executebuiltin("Skin.SetString(" + self.THUMBNAIL + "," +
                                        selectedShortcut.getProperty("icon") + ")")
                if self.THUMBNAIL is not None and selectedShortcut.getProperty("thumbnail"):
                    xbmc.executebuiltin("Skin.SetString(" + self.THUMBNAIL + "," +
                                        selectedShortcut.getProperty("thumbnail") + ")")
                if self.LIST is not None:
                    xbmc.executebuiltin("Skin.SetString(" + self.LIST + "," +
                                        self.data_func.getListProperty(path) + ")")
            elif selectedShortcut is not None and selectedShortcut.getLabel() == "::NONE::":
                # Clear the skin strings
                if self.LABEL is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.LABEL + ")")
                if self.ACTION is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.ACTION + " )")
                if self.SHORTCUTTYPE is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.SHORTCUTTYPE + ")")
                if self.THUMBNAIL is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.THUMBNAIL + ")")
                if self.THUMBNAIL is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.THUMBNAIL + ")")
                if self.LIST is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.LIST + ")")

        if self.TYPE == "widgets":
            # We're just going to choose a widget, and save its details to the given
            # skin labels

            # Load library shortcuts in thread
            thread.start_new_thread(self.lib_func.load_all_library, ())

            # Check if we should show the custom option (if the relevant widgetPath skin
            # string is provided and isn't empty)
            showCustom = False
            if self.WIDGETPATH and \
                    xbmc.getCondVisibility("!String.IsEmpty(Skin.String(%s))" % self.WIDGETPATH):
                showCustom = True

            if self.GROUPING:
                if self.GROUPING.lower() == "default":
                    selectedShortcut = self.lib_func.select_shortcut("", custom=showCustom,
                                                                     showNone=self.NONE)
                else:
                    selectedShortcut = self.lib_func.select_shortcut(
                        "", grouping=self.GROUPING,
                        custom=showCustom, showNone=self.NONE
                    )
            else:
                selectedShortcut = self.lib_func.select_shortcut(
                    "", grouping="widget",
                    custom=showCustom, showNone=self.NONE
                )

            # Now set the skin strings
            if selectedShortcut is None:
                # The user cancelled
                return

            elif selectedShortcut.getProperty("Path") and \
                    selectedShortcut.getProperty("custom") == "true":
                # The user updated the path - so we just set that property
                xbmc.executebuiltin(
                    "Skin.SetString(%s,%s)" %
                    (self.WIDGETPATH, unquote(selectedShortcut.getProperty("Path")))
                )

            elif selectedShortcut.getProperty("Path"):
                # The user selected the widget they wanted
                if self.WIDGET:
                    if selectedShortcut.getProperty("widget"):
                        xbmc.executebuiltin("Skin.SetString(%s,%s)" %
                                            (self.WIDGET, selectedShortcut.getProperty("widget")))
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGET)
                if self.WIDGETTYPE:
                    if selectedShortcut.getProperty("widgetType"):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (self.WIDGETTYPE, selectedShortcut.getProperty("widgetType"))
                        )
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGETTYPE)
                if self.WIDGETNAME:
                    if selectedShortcut.getProperty("widgetName"):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (self.WIDGETNAME, selectedShortcut.getProperty("widgetName"))
                        )
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGETNAME)
                if self.WIDGETTARGET:
                    if selectedShortcut.getProperty("widgetTarget"):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (self.WIDGETTARGET, selectedShortcut.getProperty("widgetTarget"))
                        )
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGETTARGET)
                if self.WIDGETPATH:
                    if selectedShortcut.getProperty("widgetPath"):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (self.WIDGETPATH, unquote(selectedShortcut.getProperty("widgetPath")))
                        )
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGETPATH)

            elif selectedShortcut.getLabel() == "::NONE::":
                # Clear the skin strings
                if self.WIDGET is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.WIDGET + ")")
                if self.WIDGETTYPE is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.WIDGETTYPE + " )")
                if self.WIDGETNAME is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.WIDGETNAME + ")")
                if self.WIDGETTARGET is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.WIDGETTARGET + ")")
                if self.WIDGETPATH is not None:
                    xbmc.executebuiltin("Skin.Reset(" + self.WIDGETPATH + ")")

        if self.TYPE == "context":
            # Context menu addon asking us to add a folder to the menu
            if not xbmc.getCondVisibility("Skin.HasSetting(SkinShortcuts-FullMenu)"):
                xbmcgui.Dialog().ok(ADDON_NAME, ADDON.getLocalizedString(32116))
            else:
                self.node_func.add_to_menu(self.CONTEXTFILENAME, self.CONTEXTLABEL, self.CONTEXTICON,
                                           self.CONTEXTCONTENT, self.CONTEXTWINDOW, self.data_func)

        if self.TYPE == "setProperty":
            # External request to set properties of a menu item
            self.node_func.set_properties(self.PROPERTIES, self.VALUES, self.LABELID,
                                          self.GROUPNAME, self.data_func)

        if self.TYPE == "resetall":
            # Tell XBMC not to try playing any media
            try:
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False,
                                          listitem=xbmcgui.ListItem())
            except:
                log("Not launched from a list item")
            self._reset_all_shortcuts()

    def _parse_argv(self):
        params = {}
        try:
            params = dict(parse_qsl(sys.argv[1]))
        except:
            try:
                params = dict(parse_qsl(sys.argv[2].lstrip('?')))
            except:
                pass

        self.TYPE = params.get("type", "")
        self.GROUP = params.get("group", "")
        self.GROUPNAME = params.get("groupname", None)
        self.GROUPING = params.get("grouping", None)
        self.PATH = params.get("path", "")
        self.MENUID = params.get("mainmenuID", "0")
        self.NEXTACTION = params.get("action", "0")
        self.LEVELS = params.get("levels", "0")
        self.MODE = params.get("mode", None)
        self.CHANNEL = params.get("channel", None)

        # Properties when using LIBRARY._displayShortcuts
        self.LABEL = params.get("skinLabel", None)
        self.ACTION = params.get("skinAction", None)
        self.SHORTCUTTYPE = params.get("skinType", None)
        self.THUMBNAIL = params.get("skinThumbnail", None)
        self.LIST = params.get("skinList", None)
        self.CUSTOM = params.get("custom", "False")
        self.NONE = params.get("showNone", "False")

        self.WIDGET = params.get("skinWidget", None)
        self.WIDGETTYPE = params.get("skinWidgetType", None)
        self.WIDGETNAME = params.get("skinWidgetName", None)
        self.WIDGETTARGET = params.get("skinWidgetTarget", None)
        self.WIDGETPATH = params.get("skinWidgetPath", None)

        if self.CUSTOM == "True" or self.CUSTOM == "true":
            self.CUSTOM = True
        else:
            self.CUSTOM = False
        if self.NONE == "True" or self.NONE == "true":
            self.NONE = True
        else:
            self.NONE = False

        self.NOLABELS = params.get("nolabels", "false").lower()
        self.OPTIONS = params.get("options", "").split("|")
        self.MINITEMS = int(params.get("minitems", "0"))
        self.WARNING = params.get("warning", None)
        self.DEFAULTGROUP = params.get("defaultGroup", None)

        # Properties from context menu addon
        self.CONTEXTFILENAME = unquote(params.get("filename", ""))
        self.CONTEXTLABEL = params.get("label", "")
        self.CONTEXTICON = params.get("icon", "")
        self.CONTEXTCONTENT = params.get("content", "")
        self.CONTEXTWINDOW = params.get("window", "")

        # Properties from external request to set properties
        self.PROPERTIES = unquote(params.get("property", ""))
        self.VALUES = unquote(params.get("value", ""))
        self.LABELID = params.get("labelID", "")

    # -----------------
    # PRIMARY FUNCTIONS
    # -----------------

    def _launch_shortcut(self):
        action = unquote(self.PATH)

        if action.find("::MULTIPLE::") == -1:
            # Single action, run it
            xbmc.executebuiltin(action)
        else:
            # Multiple actions, separated by |
            actions = action.split("|")
            for singleAction in actions:
                if singleAction != "::MULTIPLE::":
                    xbmc.executebuiltin(singleAction)

    @staticmethod
    def _manage_shortcuts(group, defaultGroup, nolabels, groupname):
        if HOME_WINDOW.getProperty("skinshortcuts-loading") and \
                int(calendar.timegm(gmtime())) - \
                int(HOME_WINDOW.getProperty("skinshortcuts-loading")) <= 5:
            return

        HOME_WINDOW.setProperty("skinshortcuts-loading", str(calendar.timegm(gmtime())))
        from . import gui
        ui = gui.GUI("script-skinshortcuts.xml", CWD, "default", group=group,
                     defaultGroup=defaultGroup, nolabels=nolabels, groupname=groupname)
        ui.doModal()
        del ui

        # Update home window property (used to automatically refresh type=settings)
        HOME_WINDOW.setProperty("skinshortcuts", strftime("%Y%m%d%H%M%S", gmtime()))

        # Clear window properties for this group, and for backgrounds, widgets, properties
        HOME_WINDOW.clearProperty("skinshortcuts-" + group)
        HOME_WINDOW.clearProperty("skinshortcutsWidgets")
        HOME_WINDOW.clearProperty("skinshortcutsCustomProperties")
        HOME_WINDOW.clearProperty("skinshortcutsBackgrounds")

    def _reset_all_shortcuts(self):
        log("### Resetting all shortcuts")
        dialog = xbmcgui.Dialog()

        shouldRun = None
        if self.WARNING is not None and self.WARNING.lower() == "false":
            shouldRun = True

        # Ask the user if they're sure they want to do this
        if shouldRun is None:
            shouldRun = dialog.yesno(LANGUAGE(32037), LANGUAGE(32038))

        if shouldRun:
            isShared = self.data_func.checkIfMenusShared()
            for files in xbmcvfs.listdir(DATA_PATH):
                # Try deleting all shortcuts
                if files:
                    for file in files:
                        deleteFile = False
                        if file == "settings.xml":
                            continue
                        if isShared:
                            deleteFile = True
                        elif file.startswith(SKIN_DIR) and \
                                (file.endswith(".properties") or file.endswith(".DATA.xml")):
                            deleteFile = True

                        # if file != "settings.xml" and ( not isShared or
                        # file.startswith( "%s-" %( xbmc.getSkinDir() ) ) ) or
                        # file == "%s.properties" %( xbmc.getSkinDir() ):
                        if deleteFile:
                            file_path = os.path.join(DATA_PATH, file)
                            if xbmcvfs.exists(file_path):
                                try:
                                    xbmcvfs.delete(file_path)
                                except:
                                    print_exc()
                                    log("### ERROR could not delete file %s" % file)
                        else:
                            log("Not deleting file %s" % [file])

            # Update home window property (used to automatically refresh type=settings)
            HOME_WINDOW.setProperty("skinshortcuts", strftime("%Y%m%d%H%M%S", gmtime()))

    # Functions for providing whoe menu in single list
    @staticmethod
    def _hidesubmenu(menuid):
        count = 0
        while xbmc.getCondVisibility(
                "!String.IsEmpty(Container(%s).ListItem(%i).Property(isSubmenu))" % (menuid, count)
        ):
            count -= 1

        if count != 0:
            xbmc.executebuiltin("Control.Move(" + menuid + "," + str(count) + " )")

        xbmc.executebuiltin("ClearProperty(submenuVisibility, 10000)")

    @staticmethod
    def _resetlist(menuid, action):
        count = 0
        while xbmc.getCondVisibility(
                "!String.IsEmpty(Container(%s).ListItemNoWrap(%i).Label)" % (menuid, count)
        ):
            count -= 1

        count += 1

        if count != 0:
            xbmc.executebuiltin("Control.Move(" + menuid + "," + str(count) + " )")

        xbmc.executebuiltin(unquote(action))


if __name__ == "__main__":
    log('script version %s started' % ADDON_VERSION)

    # Uncomment when profiling performance
    # filename = os.path.join( DATA_PATH, strftime( "%Y%m%d%H%M%S",gmtime() ) + "-" +
    # str( random.randrange(0,100000) ) + ".log" )
    # cProfile.run( 'Main()', filename )

    # stream = open( filename + ".txt", 'w')
    # p = pstats.Stats( filename, stream = stream )
    # p.sort_stats( "cumulative" )
    # p.print_stats()

    # Comment out the following line when profiling performance
    Main()

    log('script stopped')
