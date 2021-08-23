# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from skinshorcuts import skinshortcuts  # pylint: disable=import-error
from skinshorcuts.common import log  # pylint: disable=import-error
from skinshorcuts.constants import ADDON_VERSION  # pylint: disable=import-error

log('script version %s started' % ADDON_VERSION)
skinshortcuts.Main()
log('script stopped')
