# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import os
import re
import xml.etree.ElementTree as xmltree
from traceback import print_exc

import xbmc
import xbmcgui
import xbmcvfs
from . import datafunctions
from . import template
from .common import log
from .common import read_file
from .common import toggle_debug_logging
from .constants import ADDON
from .constants import ADDON_VERSION
from .constants import HOME_WINDOW
from .constants import KODI_VERSION
from .constants import LANGUAGE
from .constants import SKIN_DIR
from .constants import SKIN_PATH
from .hash_utils import generate_file_hash
from .hash_utils import read_hashes
from .hash_utils import write_hashes


class XMLFunctions:
    def __init__(self):
        self.data_func = datafunctions.DataFunctions()

        self.MAINWIDGET = {}
        self.MAINBACKGROUND = {}
        self.MAINPROPERTIES = {}
        self.hasSettings = False
        self.widgetCount = 1

        self.loadedPropertyPatterns = False
        self.propertyPatterns = None

        self.skinDir = SKIN_PATH

        self.checkForShortcuts = []

    def buildMenu(self, mainmenuID, groups, numLevels, buildMode, options, minitems,
                  weEnabledSystemDebug=False, weEnabledScriptDebug=False):
        # Entry point for building includes.xml files
        if HOME_WINDOW.getProperty("skinshortcuts-isrunning") == "True":
            return

        HOME_WINDOW.setProperty("skinshortcuts-isrunning", "True")

        # Get a list of profiles
        fav_file = xbmcvfs.translatePath('special://userdata/profiles.xml')
        tree = None
        if xbmcvfs.exists(fav_file):
            contents = read_file(fav_file)
            tree = xmltree.fromstring(contents)

        profilelist = []
        if tree is not None:
            profiles = tree.findall("profile")
            for profile in profiles:
                name = profile.find("name").text
                _dir = profile.find("directory").text
                log("Profile found: " + name + " (" + _dir + ")")

                # Localise the directory
                if "://" in _dir:
                    _dir = xbmcvfs.translatePath(_dir)
                # Base if off of the master profile
                _dir = xbmcvfs.translatePath(os.path.join("special://masterprofile", _dir))
                profilelist.append([_dir, "String.IsEqual(System.ProfileName,%s)" % name, name])

        else:
            profilelist = [["special://masterprofile", None]]

        shouldwerun = self.shouldwerun(profilelist)
        if shouldwerun is False:
            log("Menu is up to date")
            HOME_WINDOW.clearProperty("skinshortcuts-isrunning")
            return

        # Create a progress dialog
        progress = xbmcgui.DialogProgressBG()
        progress.create(ADDON.getAddonInfo("name"), LANGUAGE(32049))
        progress.update(0)

        # Write the menus
        try:
            self.writexml(profilelist, mainmenuID, groups, numLevels, buildMode,
                          progress, options, minitems)
            complete = True
        except:
            log("Failed to write menu")
            print_exc()
            complete = False

        # Mark that we're no longer running, clear the progress dialog
        HOME_WINDOW.clearProperty("skinshortcuts-isrunning")
        progress.close()

        if complete is True:
            # Menu is built, reload the skin
            xbmc.executebuiltin("ReloadSkin()")
        else:
            # Menu couldn't be built - generate a debug log

            # If we enabled debug logging
            if weEnabledSystemDebug or weEnabledScriptDebug:
                # Disable any logging we enabled
                if weEnabledSystemDebug:
                    toggle_debug_logging(enable=False)
                if weEnabledScriptDebug:
                    ADDON.setSetting("enable_logging", "false")

                # Offer to upload a debug log
                if xbmc.getCondVisibility("System.HasAddon(script.kodi.loguploader)"):
                    ret = xbmcgui.Dialog().yesno(ADDON.getAddonInfo("name"),
                                                 LANGUAGE(32092) + "[CR]" + LANGUAGE(32093))
                    if ret:
                        xbmc.executebuiltin("RunScript(script.kodi.loguploader)")
                else:
                    xbmcgui.Dialog().ok(ADDON.getAddonInfo("name"),
                                        LANGUAGE(32092) + "[CR]" + LANGUAGE(32094))

            else:
                # Enable any debug logging needed
                enabledSystemDebug = False
                enabledScriptDebug = False

                if toggle_debug_logging(enable=True):
                    enabledSystemDebug = True

                if not ADDON.getSettingBool("enable_logging"):
                    ADDON.setSetting("enable_logging", "true")
                    enabledScriptDebug = True

                if enabledSystemDebug or enabledScriptDebug:
                    # We enabled one or more of the debug options, re-run this function
                    self.buildMenu(mainmenuID, groups, numLevels, buildMode, options, minitems,
                                   enabledSystemDebug, enabledScriptDebug)
                else:
                    # Offer to upload a debug log
                    if xbmc.getCondVisibility("System.HasAddon( script.kodi.loguploader )"):
                        ret = xbmcgui.Dialog().yesno(ADDON.getAddonInfo("name"),
                                                     LANGUAGE(32092) + "[CR]" + LANGUAGE(32093))
                        if ret:
                            xbmc.executebuiltin("RunScript(script.kodi.loguploader)")
                    else:
                        xbmcgui.Dialog().ok(ADDON.getAddonInfo("name"),
                                            LANGUAGE(32092) + "[CR]" + LANGUAGE(32094))

    @staticmethod
    def shouldwerun(profilelist):
        try:
            prop = HOME_WINDOW.getProperty("skinshortcuts-reloadmainmenu")
            HOME_WINDOW.clearProperty("skinshortcuts-reloadmainmenu")
            if prop == "True":
                log("Menu has been edited")
                return True
        except:
            pass

        # Save some settings to skin strings
        xbmc.executebuiltin("Skin.SetString(skinshortcuts-sharedmenu,%s)" %
                            (ADDON.getSetting("shared_menu")))

        # Get the skins addon.xml file
        addonpath = xbmcvfs.translatePath(os.path.join("special://skin/", 'addon.xml'))
        addon = xmltree.parse(addonpath)
        extensionpoints = addon.findall("extension")
        paths = []
        skinpaths = []

        # Get the skin version
        skinVersion = addon.getroot().attrib.get("version")

        # Get the directories for resolutions this skin supports
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get("point") == "xbmc.gui.skin":
                resolutions = extensionpoint.findall("res")
                for resolution in resolutions:
                    path = xbmcvfs.translatePath(
                        os.path.join("special://skin/", resolution.attrib.get("folder"),
                                     "script-skinshortcuts-includes.xml")
                    )
                    paths.append(path)
                    skinpaths.append(path)

        # Check for the includes file
        for path in paths:
            if not xbmcvfs.exists(path):
                log("Includes file does not exist")
                return True
            else:
                pass

        hashes = read_hashes()
        if not hashes:
            log("No hashes found")
            return True

        checkedXBMCVer = False
        checkedSkinVer = False
        checkedScriptVer = False
        checkedProfileList = False
        checkedPVRVis = False
        checkedSharedMenu = False
        foundFullMenu = False

        for hashed in hashes:
            hashed_item = '' if not hashed else hashed[0]
            hashed_value = '' if len(hashed) < 2 else hashed[1]

            log("Comparing hashes of Item: %s Value: %s" %
                (hashed_item, hashed_value))

            if hashed_value is not None:
                if hashed_item == "::XBMCVER::":
                    # Check the skin version is still the same as hashed_value
                    checkedXBMCVer = True
                    if KODI_VERSION != hashed_value:
                        log("Now running a different version of Kodi")
                        return True
                elif hashed_item == "::SKINVER::":
                    # Check the skin version is still the same as hashed_value
                    checkedSkinVer = True
                    if skinVersion != hashed_value:
                        log("Now running a different skin version")
                        return True
                elif hashed_item == "::SCRIPTVER::":
                    # Check the script version is still the same as hashed_value
                    checkedScriptVer = True
                    if ADDON_VERSION != hashed_value:
                        log("Now running a different script version")
                        return True
                elif hashed_item == "::PROFILELIST::":
                    # Check the profilelist is still the same as hashed_value
                    checkedProfileList = True
                    if profilelist != hashed_value:
                        log("Profiles have changes")
                        return True
                elif hashed_item == "::HIDEPVR::":
                    checkedPVRVis = True
                    if ADDON.getSetting("donthidepvr") != hashed_value:
                        log("PVR visibility setting has changed")
                elif hashed_item == "::SHARED::":
                    # Check whether shared-menu setting has changed
                    checkedSharedMenu = True
                    if ADDON.getSetting("shared_menu") != hashed_value:
                        log("Shared menu setting has changed")
                        return True
                elif hashed_item == "::LANGUAGE::":
                    # We no longer need to rebuild on a system language change
                    pass
                elif hashed_item == "::SKINBOOL::":
                    # A boolean we need to set (if profile matches)
                    if xbmc.getCondVisibility(hashed_value[0]):
                        if hashed_value[2] == "True":
                            xbmc.executebuiltin("Skin.SetBool(%s)" % (hashed_value[1]))
                        else:
                            xbmc.executebuiltin("Skin.Reset(%s)" % (hashed_value[1]))
                elif hashed_item == "::FULLMENU::":
                    # Mark that we need to set the fullmenu bool
                    foundFullMenu = True
                elif hashed_item == "::SKINDIR::":
                    # Used to import menus from one skin to another, nothing to check here
                    pass
                else:
                    try:
                        hexdigest = generate_file_hash(hashed_item)
                        if hexdigest != hashed_value:
                            log("Hash does not match for Filename: %s "
                                "Stored Hash: %s Actual Hash: %s" %
                                (hashed_item, hashed_value, hexdigest))
                            return True
                    except:
                        item = 'UNKNOWN' if not hashed_item else hashed_item
                        value = 'UNKNOWN' if hashed_value == '' else hashed_value
                        log("Failed to compare hash of Item: %s Value: %s" %
                            (item, value))

            else:
                if xbmcvfs.exists(hashed_item):
                    log("File now exists " + hashed_item)
                    return True

        # Set or clear the FullMenu skin bool
        if foundFullMenu:
            xbmc.executebuiltin("Skin.SetBool(SkinShortcuts-FullMenu)")
        else:
            xbmc.executebuiltin("Skin.Reset(SkinShortcuts-FullMenu)")

        # If the skin or script version, or profile list, haven't been checked,
        # we need to rebuild the menu (most likely we're running an old version of the script)
        if checkedXBMCVer is False or checkedSkinVer is False or checkedScriptVer is False or \
                checkedProfileList is False or checkedPVRVis is False or \
                checkedSharedMenu is False:
            return True

        # If we get here, the menu does not need to be rebuilt.
        return False

    # noinspection PyListCreation
    def writexml(self, profilelist, mainmenuID, groups, numLevels, buildMode,
                 progress, options, minitems):
        # Reset the hashlist, add the profile list and script version
        hashlist = []
        hashlist.append(["::PROFILELIST::", profilelist])
        hashlist.append(["::SCRIPTVER::", ADDON_VERSION])
        hashlist.append(["::XBMCVER::", KODI_VERSION])
        hashlist.append(["::HIDEPVR::", ADDON.getSetting("donthidepvr")])
        hashlist.append(["::SHARED::", ADDON.getSetting("shared_menu")])
        hashlist.append(["::SKINDIR::", SKIN_DIR])

        # Clear any skin settings for backgrounds and widgets
        self.data_func.reset_backgroundandwidgets()
        self.widgetCount = 1

        # Create a new tree and includes for the various groups
        tree = xmltree.ElementTree(xmltree.Element("includes"))
        root = tree.getroot()

        # Create a Template object and pass it the root
        Template = template.Template()
        Template.includes = root
        Template.progress = progress

        # Get any shortcuts we're checking for
        self.checkForShortcuts = []
        overridestree = self.data_func.get_overrides_skin()
        checkForShortcutsOverrides = overridestree.getroot().findall("checkforshortcut")
        for checkForShortcutOverride in checkForShortcutsOverrides:
            if "property" in checkForShortcutOverride.attrib:
                # Add this to the list of shortcuts we'll check for
                self.checkForShortcuts.append((checkForShortcutOverride.text.lower(),
                                               checkForShortcutOverride.attrib.get("property"),
                                               "False"))

        mainmenuTree = xmltree.SubElement(root, "include")
        mainmenuTree.set("name", "skinshortcuts-mainmenu")

        submenuTrees = []
        for level in range(0, int(numLevels) + 1):
            _ = xmltree.SubElement(root, "include")
            subtree = xmltree.SubElement(root, "include")
            if level == 0:
                subtree.set("name", "skinshortcuts-submenu")
            else:
                subtree.set("name", "skinshortcuts-submenu-" + str(level))
            if subtree not in submenuTrees:
                submenuTrees.append(subtree)

        allmenuTree = []
        if buildMode == "single":
            allmenuTree = xmltree.SubElement(root, "include")
            allmenuTree.set("name", "skinshortcuts-allmenus")

        profilePercent = 100 / len(profilelist)
        profileCount = -1

        submenuNodes = {}

        for profile in profilelist:
            log("Building menu for profile %s" % (profile[2]))
            # Load profile details
            profileCount += 1

            # Reset whether we have settings
            self.hasSettings = False

            # Reset any checkForShortcuts to say we haven't found them
            newCheckForShortcuts = []
            for checkforShortcut in self.checkForShortcuts:
                newCheckForShortcuts.append((checkforShortcut[0], checkforShortcut[1], "False"))
            self.checkForShortcuts = newCheckForShortcuts

            # Clear any previous labelID's
            self.data_func.clear_labelID()

            # Clear any additional properties, which may be for a different profile
            self.data_func.currentProperties = None

            # Create objects to hold the items
            menuitems = []
            submenuItems = []
            templateMainMenuItems = xmltree.Element("includes")

            # If building the main menu, split the mainmenu shortcut nodes into the menuitems list
            fullMenu = False
            if groups == "" or groups.split("|")[0] == "mainmenu":
                # Set a skinstring that marks that we're providing the whole menu
                xbmc.executebuiltin("Skin.SetBool(SkinShortcuts-FullMenu)")
                hashlist.append(["::FULLMENU::", "True"])
                for node in self.data_func.get_shortcuts("mainmenu", profileDir=profile[0]) \
                        .findall("shortcut"):
                    menuitems.append(node)
                    submenuItems.append(node)
                fullMenu = True
            else:
                # Clear any skinstring marking that we're providing the whole menu
                xbmc.executebuiltin("Skin.Reset(SkinShortcuts-FullMenu)")
                hashlist.append(["::FULLMENU::", "False"])

            # If building specific groups, split them into the menuitems list
            count = 0
            if groups != "":
                for group in groups.split("|"):
                    if count != 0 or group != "mainmenu":
                        menuitems.append(group)

            if len(menuitems) == 0:
                # No groups to build
                break

            itemidmainmenu = 0
            if len(Template.otherTemplates) == 0:
                percent = profilePercent / len(menuitems)
            else:
                percent = float(profilePercent) / float(len(menuitems) * 2)
            Template.percent = percent * (len(menuitems))

            i = 0
            for item in menuitems:
                i += 1
                itemidmainmenu += 1
                currentProgress = (profilePercent * profileCount) + (percent * i)
                progress.update(int(currentProgress))
                Template.current = currentProgress
                submenuDefaultID = None
                templateCurrentMainMenuItem = None

                if not isinstance(item, str):
                    # This is a main menu item (we know this because it's an element, not a string)
                    submenu = item.find("labelID").text

                    # Build the menu item
                    menuitem, allProps = self.buildElement(
                        item,
                        "mainmenu",
                        None,
                        profile[1], self.data_func.slugify(submenu, convertInteger=True),
                        itemid=itemidmainmenu,
                        options=options
                    )

                    # Save a copy for the template
                    templateMainMenuItems.append(Template.copy_tree(menuitem))
                    templateCurrentMainMenuItem = Template.copy_tree(menuitem)

                    # Get submenu defaultID
                    submenuDefaultID = item.find("defaultID").text

                    # Remove any template-only properties
                    otherProperties, requires, templateOnly = self.data_func.getPropertyRequires()
                    for key in otherProperties:
                        if key in list(allProps.keys()) and key in templateOnly:
                            # This key is template-only
                            menuitem.remove(allProps[key])
                            allProps.pop(key)

                    # Add the menu item to the various includes, retaining a reference to them
                    mainmenuItemA = Template.copy_tree(menuitem)
                    mainmenuTree.append(mainmenuItemA)

                    mainmenuItemB = None
                    if buildMode == "single":
                        mainmenuItemB = Template.copy_tree(menuitem)
                        allmenuTree.append(mainmenuItemB)

                else:
                    # It's an additional menu, so get its labelID
                    submenu = self.data_func.get_labelID(item, None)

                    # And clear mainmenuItemA and mainmenuItemB, so we don't
                    # incorrectly add properties to an actual main menu item
                    mainmenuItemA = None
                    mainmenuItemB = None

                # Build the submenu
                count = 0  # Used to keep track of additional submenu
                for submenuTree in submenuTrees:
                    submenuVisibilityName = submenu
                    if count == 1:
                        submenu = submenu + "." + str(count)
                    elif count != 0:
                        submenu = submenu[:-1] + str(count)
                        submenuVisibilityName = submenu[:-2]

                    justmenuTreeA = []
                    justmenuTreeB = []
                    # Get the tree's we're going to write the menu to
                    if "noGroups" not in options:
                        if submenu in submenuNodes:
                            justmenuTreeA = submenuNodes[submenu][0]
                            justmenuTreeB = submenuNodes[submenu][1]
                        else:
                            # Create these nodes
                            justmenuTreeA = xmltree.SubElement(root, "include")
                            justmenuTreeB = xmltree.SubElement(root, "include")

                            if count != 0:
                                groupInclude = self.data_func.slugify(
                                    submenu[:-2], convertInteger=True
                                ) + "-" + submenu[-1:]
                            else:
                                groupInclude = self.data_func.slugify(submenu, convertInteger=True)

                            justmenuTreeA.set("name", "skinshortcuts-group-" + groupInclude)
                            justmenuTreeB.set("name", "skinshortcuts-group-alt-" + groupInclude)

                            submenuNodes[submenu] = [justmenuTreeA, justmenuTreeB]

                    itemidsubmenu = 0

                    # Get the shortcuts for the submenu
                    if count == 0:
                        submenudata = self.data_func.get_shortcuts(submenu, submenuDefaultID,
                                                                   profile[0])
                    else:
                        submenudata = self.data_func.get_shortcuts(submenu, None,
                                                                   profile[0], isSubLevel=True)

                    if isinstance(submenudata, list):
                        submenuitems = submenudata
                    else:
                        submenuitems = submenudata.findall("shortcut")

                    # Are there any submenu items for the main menu?
                    if count == 0:
                        if len(submenuitems) != 0:
                            try:
                                hasSubMenu = xmltree.SubElement(mainmenuItemA, "property")
                                hasSubMenu.set("name", "hasSubmenu")
                                hasSubMenu.text = "True"
                                if buildMode == "single":
                                    hasSubMenu = xmltree.SubElement(mainmenuItemB, "property")
                                    hasSubMenu.set("name", "hasSubmenu")
                                    hasSubMenu.text = "True"
                            except:
                                # There probably isn't a main menu
                                pass
                        else:
                            try:
                                hasSubMenu = xmltree.SubElement(mainmenuItemA, "property")
                                hasSubMenu.set("name", "hasSubmenu")
                                hasSubMenu.text = "False"
                                if buildMode == "single":
                                    hasSubMenu = xmltree.SubElement(mainmenuItemB, "property")
                                    hasSubMenu.set("name", "hasSubmenu")
                                    hasSubMenu.text = "False"
                            except:
                                # There probably isn't a main menu
                                pass

                    # If we're building a single menu, update the onclicks of the main menu
                    if buildMode == "single" and not len(submenuitems) == 0 and \
                            not isinstance(item, str):
                        for onclickelement in mainmenuItemB.findall("onclick"):
                            if "condition" in onclickelement.attrib:
                                onclickelement.set(
                                    "condition",
                                    "String.IsEqual(Window(10000)"
                                    ".Property(submenuVisibility),%s) + [%s]" %
                                    (self.data_func.slugify(submenuVisibilityName,
                                                            convertInteger=True),
                                     onclickelement.attrib.get("condition"))
                                )
                                newonclick = xmltree.SubElement(mainmenuItemB, "onclick")
                                newonclick.text = "SetProperty(submenuVisibility," + \
                                                  self.data_func.slugify(submenuVisibilityName,
                                                                         convertInteger=True) + \
                                                  ",10000)"
                                newonclick.set("condition", onclickelement.attrib.get("condition"))
                            else:
                                onclickelement.set(
                                    "condition",
                                    "String.IsEqual(Window(10000).Property(submenuVisibility),%s)"
                                    % (self.data_func.slugify(submenuVisibilityName,
                                                              convertInteger=True))
                                )
                                newonclick = xmltree.SubElement(mainmenuItemB, "onclick")
                                newonclick.text = "SetProperty(submenuVisibility," + \
                                                  self.data_func.slugify(submenuVisibilityName,
                                                                         convertInteger=True) + \
                                                  ",10000)"

                    # Build the submenu items
                    templateSubMenuItems = xmltree.Element("includes")
                    for submenuItem in submenuitems:
                        itemidsubmenu += 1
                        # Build the item without any visibility conditions
                        menuitem, allProps = self.buildElement(submenuItem, submenu, None,
                                                               profile[1], itemid=itemidsubmenu,
                                                               mainmenuid=itemidmainmenu,
                                                               options=options)
                        isSubMenuElement = xmltree.SubElement(menuitem, "property")
                        isSubMenuElement.set("name", "isSubmenu")
                        isSubMenuElement.text = "True"

                        # Save a copy for the template
                        templateSubMenuItems.append(Template.copy_tree(menuitem))

                        # Remove any template-only properties
                        otherProperties, requires, templateOnly = \
                            self.data_func.getPropertyRequires()
                        for key in otherProperties:
                            if key in list(allProps.keys()) and key in templateOnly:
                                # This key is template-only
                                menuitem.remove(allProps[key])
                                allProps.pop(key)

                        menuitemCopy = Template.copy_tree(menuitem)

                        if "noGroups" not in options:
                            # Add it, with appropriate visibility conditions,
                            # to the various submenu includes
                            justmenuTreeA.append(menuitem)

                            visibilityElement = menuitemCopy.find("visible")
                            visibilityElement.text = "[%s] + %s" % \
                                                     (visibilityElement.text,
                                                      "String.IsEqual(Window(10000)"
                                                      ".Property(submenuVisibility),%s)" %
                                                      (self.data_func.slugify(submenuVisibilityName,
                                                                              convertInteger=True)))
                            justmenuTreeB.append(menuitemCopy)

                        if buildMode == "single" and not isinstance(item, str):
                            # Add the property 'submenuVisibility'
                            allmenuTreeCopy = Template.copy_tree(menuitemCopy)
                            submenuVisibility = xmltree.SubElement(allmenuTreeCopy, "property")
                            submenuVisibility.set("name", "submenuVisibility")
                            submenuVisibility.text = self.data_func.slugify(submenuVisibilityName,
                                                                            convertInteger=True)
                            allmenuTree.append(allmenuTreeCopy)

                        menuitemCopy = Template.copy_tree(menuitem)
                        visibilityElement = menuitemCopy.find("visible")
                        visibilityElement.text = "[%s] + %s" % \
                                                 (visibilityElement.text,
                                                  "String.IsEqual(Container(%s)"
                                                  ".ListItem.Property(submenuVisibility),%s)" %
                                                  (mainmenuID,
                                                   self.data_func.slugify(submenuVisibilityName,
                                                                          convertInteger=True)))
                        submenuTree.append(menuitemCopy)
                    if len(submenuitems) == 0 and "noGroups" not in options:
                        # There aren't any submenu items, so add a 'description'
                        # element to the group includes
                        # so that Kodi doesn't think they're invalid
                        newelement = xmltree.Element("description")
                        newelement.text = "No items"
                        justmenuTreeA.append(newelement)
                        justmenuTreeB.append(newelement)

                    # Build the template for the submenu
                    buildOthers = False
                    if item in submenuItems:
                        buildOthers = True
                    Template.parseItems(
                        "submenu", count, templateSubMenuItems, profile[2],
                        profile[1], "String.IsEqual(Container(%s).ListItem"
                                    ".Property(submenuVisibility),%s)" %
                                    (mainmenuID,
                                     self.data_func.slugify(submenuVisibilityName,
                                                            convertInteger=True)),
                        item, None, buildOthers, mainmenuitems=templateCurrentMainMenuItem)

                    count += 1

            if self.hasSettings is False:
                # Check if the overrides asks for a forced settings...
                overridestree = self.data_func.get_overrides_skin()
                forceSettings = overridestree.getroot().find("forcesettings")
                if forceSettings is not None:
                    # We want a settings option to be added
                    newelement = xmltree.SubElement(mainmenuTree, "item")
                    xmltree.SubElement(newelement, "label").text = "$LOCALIZE[10004]"
                    xmltree.SubElement(newelement, "icon").text = "DefaultShortcut.png"
                    xmltree.SubElement(newelement, "onclick").text = "ActivateWindow(settings)"
                    xmltree.SubElement(newelement, "visible").text = profile[1]

                    if buildMode == "single":
                        newelement = xmltree.SubElement(mainmenuTree, "item")
                        xmltree.SubElement(newelement, "label").text = "$LOCALIZE[10004]"
                        xmltree.SubElement(newelement, "icon").text = "DefaultShortcut.png"
                        xmltree.SubElement(newelement, "onclick").text = "ActivateWindow(settings)"
                        xmltree.SubElement(newelement, "visible").text = profile[1]

            if len(self.checkForShortcuts) != 0:
                # Add a value to the variable for all checkForShortcuts
                for checkForShortcut in self.checkForShortcuts:
                    if profile[1] is not None and xbmc.getCondVisibility(profile[1]):
                        # Current profile - set the skin bool
                        if checkForShortcut[2] == "True":
                            xbmc.executebuiltin("Skin.SetBool(%s)" % (checkForShortcut[1]))
                        else:
                            xbmc.executebuiltin("Skin.Reset(%s)" % (checkForShortcut[1]))
                    # Save this to the hashes file, so we can set it on profile changes
                    hashlist.append(["::SKINBOOL::", [profile[1], checkForShortcut[1],
                                                      checkForShortcut[2]]])

            # Build the template for the main menu
            Template.parseItems("mainmenu", 0, templateMainMenuItems, profile[2], profile[1],
                                "", "", mainmenuID, True)

            # If we haven't built enough main menu items, copy the ones we have
            while itemidmainmenu < minitems and fullMenu and len(mainmenuTree) != 0:
                updatedMenuTree = Template.copy_tree(mainmenuTree)
                for item in updatedMenuTree:
                    itemidmainmenu += 1
                    # Update ID
                    item.set("id", str(itemidmainmenu))
                    for idElement in item.findall("property"):
                        if idElement.attrib.get("name") == "id":
                            idElement.text = "$NUM[%s]" % (str(itemidmainmenu))
                    mainmenuTree.append(item)

        # Build any 'Other' templates
        Template.writeOthers()

        progress.update(100, message=LANGUAGE(32098))

        # Get the skins addon.xml file
        addon_xml = xbmcvfs.translatePath(os.path.join("special://skin/", 'addon.xml'))
        addon = xmltree.parse(addon_xml)
        extensionpoints = addon.findall("extension")

        skinVersion = addon.getroot().attrib.get("version")
        # Append the skin version to the hashlist
        hashlist.append(["::SKINVER::", skinVersion])

        # indent the tree
        self.data_func.indent(tree.getroot())

        # create a set of hashable files
        hashable = set()
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get("point") == "xbmc.gui.skin":
                resolutions = extensionpoint.findall("res")
                for resolution in resolutions:
                    path = xbmcvfs.translatePath(
                        os.path.join(self.skinDir, resolution.attrib.get("folder"),
                                     "script-skinshortcuts-includes.xml")
                    )
                    tree.write(path, encoding="UTF-8")  # writing includes
                    hashable.add(path)

        hashable.update(self.data_func.hashable)
        hashable.update(Template.hashable)

        for item in hashable:  # generate a hash for all paths
            hexdigest = generate_file_hash(item)
            if hexdigest:
                hashlist.append([item, hexdigest])

        # Save the hashes
        write_hashes(hashlist)

    def buildElement(self, item, groupName, visibilityCondition, profileVisibility,
                     submenuVisibility=None, itemid=-1, mainmenuid=None, options=None):
        # This function will build an element for the passed Item in

        if options is None:
            options = []

        # Create the element
        newelement = xmltree.Element("item")
        allProps = {}

        # Set ID
        if itemid != -1:
            newelement.set("id", str(itemid))
        idproperty = xmltree.SubElement(newelement, "property")
        idproperty.set("name", "id")
        idproperty.text = "$NUMBER[%s]" % (str(itemid))
        allProps["id"] = idproperty

        # Set main menu id
        if mainmenuid:
            mainmenuidproperty = xmltree.SubElement(newelement, "property")
            mainmenuidproperty.set("name", "mainmenuid")
            mainmenuidproperty.text = "%s" % (str(mainmenuid))
            allProps[mainmenuid] = mainmenuidproperty

        # Label and label2
        xmltree.SubElement(newelement, "label").text = \
            self.data_func.local(item.find("label").text)[1]
        xmltree.SubElement(newelement, "label2").text = \
            self.data_func.local(item.find("label2").text)[1]

        # Icon and thumb
        icon = item.find("override-icon")
        if icon is None:
            icon = item.find("icon")
        if icon is None:
            xmltree.SubElement(newelement, "icon").text = "DefaultShortcut.png"
        else:
            xmltree.SubElement(newelement, "icon").text = icon.text
        thumb = item.find("thumb")
        if thumb is not None:
            xmltree.SubElement(newelement, "thumb").text = item.find("thumb").text

        # labelID and defaultID
        labelID = xmltree.SubElement(newelement, "property")
        labelID.text = item.find("labelID").text
        labelID.set("name", "labelID")
        allProps["labelID"] = labelID
        defaultID = xmltree.SubElement(newelement, "property")
        defaultID.text = item.find("defaultID").text
        defaultID.set("name", "defaultID")
        allProps["defaultID"] = defaultID

        # Check if the item is disabled
        if item.find("disabled") is not None:
            # It is, so we set it to be invisible, add an empty onclick and return
            xmltree.SubElement(newelement, "visible").text = "False"
            xmltree.SubElement(newelement, "onclick").text = "noop"
            return newelement, allProps

        # Clear cloned options if main menu
        if groupName == "mainmenu":
            self.MAINWIDGET = {}
            self.MAINBACKGROUND = {}
            self.MAINPROPERTIES = {}

        # Additional properties
        properties = eval(item.find("additional-properties").text)
        if len(properties) != 0:
            for prop in properties:
                if prop[0] == "node.visible":
                    visibleProperty = xmltree.SubElement(newelement, "visible")
                    visibleProperty.text = prop[1]
                else:
                    additionalproperty = xmltree.SubElement(newelement, "property")
                    additionalproperty.set("name", prop[0])
                    additionalproperty.text = prop[1]
                    allProps[prop[0]] = additionalproperty

                    # If this is a widget or background, set a skin setting to say it's enabled
                    if prop[0] == "widget":
                        xbmc.executebuiltin("Skin.SetBool(skinshortcuts-widget-" + prop[1] + ")")
                        # And if it's the main menu, list it
                        if groupName == "mainmenu":
                            xbmc.executebuiltin("Skin.SetString(skinshortcuts-widget-" +
                                                str(self.widgetCount) + "," + prop[1] + ")")
                            self.widgetCount += 1
                    elif prop[0] == "background":
                        xbmc.executebuiltin("Skin.SetBool(skinshortcuts-background-" +
                                            prop[1] + ")")

                    # If this is the main menu, and we're cloning widgets,
                    # backgrounds or properties...
                    if groupName == "mainmenu":
                        if "clonewidgets" in options:
                            widgetProperties = ["widget", "widgetName", "widgetType",
                                                "widgetTarget", "widgetPath", "widgetPlaylist"]
                            if prop[0] in widgetProperties:
                                self.MAINWIDGET[prop[0]] = prop[1]
                        if "clonebackgrounds" in options:
                            backgroundProperties = ["background", "backgroundName",
                                                    "backgroundPlaylist", "backgroundPlaylistName"]
                            if prop[0] in backgroundProperties:
                                self.MAINBACKGROUND[prop[0]] = prop[1]
                        if "cloneproperties" in options:
                            self.MAINPROPERTIES[prop[0]] = prop[1]

                    # For backwards compatibility, save widgetPlaylist as widgetPath too
                    if prop[0] == "widgetPlaylist":
                        additionalproperty = xmltree.SubElement(newelement, "property")
                        additionalproperty.set("name", "widgetPath")
                        additionalproperty.text = prop[1]

        # Get fallback properties, property requirements, templateOnly value of properties
        fallbackProperties, fallbacks = self.data_func.getCustomPropertyFallbacks(groupName)

        # Add fallback properties
        for key in fallbackProperties:
            if key not in list(allProps.keys()):
                # Check whether we have a fallback for the value
                for propertyMatch in fallbacks[key]:
                    matches = False
                    if propertyMatch[1] is None:
                        # This has no conditions, so it matched
                        matches = True
                    else:
                        # This has an attribute and a value to match against
                        for prop in properties:
                            if prop[0] == propertyMatch[1] and prop[1] == propertyMatch[2]:
                                matches = True
                                break

                    if matches:
                        additionalproperty = xmltree.SubElement(newelement, "property")
                        additionalproperty.set("name", key)
                        additionalproperty.text = propertyMatch[0]
                        allProps[key] = additionalproperty
                        break

        # Get property requirements
        otherProperties, requires, templateOnly = self.data_func.getPropertyRequires()

        # Remove any properties whose requirements haven't been met
        for key in otherProperties:
            if key in list(allProps.keys()) and key in list(requires.keys()) and \
                    requires[key] not in list(allProps.keys()):
                # This properties requirements aren't met
                newelement.remove(allProps[key])
                allProps.pop(key)

        # Primary visibility
        visibility = item.find("visibility")
        if visibility is not None:
            xmltree.SubElement(newelement, "visible").text = visibility.text

        # additional onclick (group overrides)
        onclicks = item.findall("additional-action")
        for onclick in onclicks:
            onclickelement = xmltree.SubElement(newelement, "onclick")
            onclickelement.text = onclick.text
            if "condition" in onclick.attrib:
                onclickelement.set("condition", onclick.attrib.get("condition"))

        # Onclick
        onclicks = item.findall("override-action")
        if len(onclicks) == 0:
            onclicks = item.findall("action")

        for onclick in onclicks:
            onclickelement = xmltree.SubElement(newelement, "onclick")

            # Updrage action if necessary
            onclick.text = self.data_func.upgradeAction(onclick.text)

            # PVR Action
            if onclick.text.startswith("pvr-channel://"):
                # PVR action
                onclickelement.text = "RunScript(script.skinshortcuts,type=launchpvr&channel=" + \
                                      onclick.text.replace("pvr-channel://", "") + ")"
            elif onclick.text.startswith("ActivateWindow(") and SKIN_PATH in onclick.text:
                # Skin-relative links
                try:
                    actionParts = onclick.text[15:-1].split(",")
                    actionParts[1] = actionParts[1].replace(SKIN_PATH, "")
                    _ = actionParts[1].split(os.sep)
                    newAction = "special://skin"
                    for actionPart in actionParts[1].split(os.sep):
                        if actionPart != "":
                            newAction = newAction + "/" + actionPart
                    if len(actionParts) == 2:
                        onclickelement.text = "ActivateWindow(" + actionParts[0] + "," + \
                                              newAction + ")"
                    else:
                        onclickelement.text = "ActivateWindow(" + actionParts[0] + "," + \
                                              newAction + "," + actionParts[2] + ")"
                except:
                    pass
            else:
                onclickelement.text = onclick.text

            # Also add it as a path property
            if not self.propertyExists("path", newelement) and "path" not in list(allProps.keys()):
                # we only add the path property if there isn't already one in the list
                # because it has to be unique in Kodi lists
                pathelement = xmltree.SubElement(newelement, "property")
                pathelement.set("name", "path")
                pathelement.text = onclickelement.text
                allProps["path"] = pathelement

            # Get 'list' property (the action property of an ActivateWindow shortcut)
            if not self.propertyExists("list", newelement) and "list" not in list(allProps.keys()):
                # we only add the list property if there isn't already one in the list
                # because it has to be unique in Kodi lists
                listElement = xmltree.SubElement(newelement, "property")
                listElement.set("name", "list")
                listElement.text = \
                    self.data_func.getListProperty(onclickelement.text.replace('"', ''))
                allProps["list"] = listElement

            if onclick.text == "ActivateWindow(Settings)":
                self.hasSettings = True

            if "condition" in onclick.attrib:
                onclickelement.set("condition", onclick.attrib.get("condition"))

            if len(self.checkForShortcuts) != 0:
                # Check if we've been asked to watch for this shortcut
                newCheckForShortcuts = []
                for checkforShortcut in self.checkForShortcuts:
                    if onclick.text.lower() == checkforShortcut[0]:
                        # They match, change the value to True
                        newCheckForShortcuts.append((checkforShortcut[0],
                                                     checkforShortcut[1], "True"))
                    else:
                        newCheckForShortcuts.append(checkforShortcut)
                self.checkForShortcuts = newCheckForShortcuts

        # Visibility
        if visibilityCondition is not None:
            visibilityElement = xmltree.SubElement(newelement, "visible")
            if profileVisibility is not None:
                visibilityElement.text = profileVisibility + " + [" + visibilityCondition + "]"
            else:
                visibilityElement.text = visibilityCondition
            issubmenuElement = xmltree.SubElement(newelement, "property")
            issubmenuElement.set("name", "isSubmenu")
            issubmenuElement.text = "True"
            allProps["isSubmenu"] = issubmenuElement
        elif profileVisibility is not None:
            visibilityElement = xmltree.SubElement(newelement, "visible")
            visibilityElement.text = profileVisibility

        # Submenu visibility
        if submenuVisibility is not None:
            submenuVisibilityElement = xmltree.SubElement(newelement, "property")
            submenuVisibilityElement.set("name", "submenuVisibility")
            if submenuVisibility.isdigit():
                submenuVisibilityElement.text = "$NUMBER[" + submenuVisibility + "]"
            else:
                submenuVisibilityElement.text = self.data_func.slugify(submenuVisibility)

        # Group name
        group = xmltree.SubElement(newelement, "property")
        group.set("name", "group")
        group.text = groupName
        allProps["group"] = group

        # If this isn't the main menu, and we're cloning widgets or backgrounds...
        if groupName != "mainmenu":
            if "clonewidgets" in options and len(self.MAINWIDGET) != 0:
                for key in self.MAINWIDGET:
                    additionalproperty = xmltree.SubElement(newelement, "property")
                    additionalproperty.set("name", key)
                    additionalproperty.text = self.MAINWIDGET[key]
                    allProps[key] = additionalproperty
            if "clonebackgrounds" in options and len(self.MAINBACKGROUND) != 0:
                for key in self.MAINBACKGROUND:
                    additionalproperty = xmltree.SubElement(newelement, "property")
                    additionalproperty.set("name", key)
                    additionalproperty.text = self.data_func.local(self.MAINBACKGROUND[key])[1]
                    allProps[key] = additionalproperty
            if "cloneproperties" in options and len(self.MAINPROPERTIES) != 0:
                for key in self.MAINPROPERTIES:
                    additionalproperty = xmltree.SubElement(newelement, "property")
                    additionalproperty.set("name", key)
                    additionalproperty.text = self.data_func.local(self.MAINPROPERTIES[key])[1]
                    allProps[key] = additionalproperty

        propertyPatterns = self.getPropertyPatterns(labelID.text, groupName)
        if len(propertyPatterns) > 0:
            propertyReplacements = self.getPropertyReplacements(newelement)
            for propertyName in propertyPatterns:
                propertyPattern = propertyPatterns[propertyName][0]
                for original, replacement in propertyReplacements:
                    regexpPattern = re.compile(re.escape(original), re.IGNORECASE)
                    propertyPattern = regexpPattern.sub(replacement.replace("\\", r"\\"),
                                                        propertyPattern)

                additionalproperty = xmltree.SubElement(newelement, "property")
                additionalproperty.set("name", propertyName)
                additionalproperty.text = propertyPattern
                allProps[propertyName] = additionalproperty

        return newelement, allProps

    def getPropertyPatterns(self, labelID, group):
        propertyPatterns = {}
        if not self.loadedPropertyPatterns:
            overrides = self.data_func.get_overrides_skin()
            self.propertyPatterns = overrides.getroot().findall("propertypattern")
            self.loadedPropertyPatterns = True

        for propertyPatternElement in self.propertyPatterns:
            propertyName = propertyPatternElement.get("property")
            propertyGroup = propertyPatternElement.get("group")

            if not propertyName or not propertyGroup or propertyGroup != group or \
                    not propertyPatternElement.text:
                continue

            propertyLabelID = propertyPatternElement.get("labelID")
            if not propertyLabelID:
                if propertyName not in propertyPatterns:
                    propertyPatterns[propertyName] = [propertyPatternElement.text, False]
            elif propertyLabelID == labelID:
                if propertyName not in propertyPatterns or \
                        propertyPatterns[propertyName][1] is False:
                    propertyPatterns[propertyName] = [propertyPatternElement.text, True]

        return propertyPatterns

    @staticmethod
    def getPropertyReplacements(element):
        propertyReplacements = []
        for subElement in list(element):
            if subElement.tag == "property":
                propertyName = subElement.get("name")
                if propertyName and subElement.text:
                    propertyReplacements.append(("::%s::" % propertyName, subElement.text))
            elif subElement.text:
                propertyReplacements.append(("::%s::" % subElement.tag, subElement.text))

        return propertyReplacements

    @staticmethod
    def propertyExists(propertyName, element):
        for item in element.findall("property"):
            if propertyName in item.attrib:
                return True
        return False

    @staticmethod
    def findIncludePosition(source_list, item):
        try:
            return source_list.index(item)
        except:
            return None
