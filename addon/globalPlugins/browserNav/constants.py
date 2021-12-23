#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import controlTypes

try:
    ROLE_EDITABLETEXT = controlTypes.ROLE_EDITABLETEXT
    ROLE_PANE = controlTypes.ROLE_PANE
    ROLE_FRAME = controlTypes.ROLE_FRAME
    ROLE_DOCUMENT = controlTypes.ROLE_DOCUMENT
    ROLE_TAB = controlTypes.ROLE_TAB
    ROLE_TABCONTROL = controlTypes.ROLE_TABCONTROL
    ROLE_APPLICATION = controlTypes.ROLE_APPLICATION
    ROLE_DIALOG = controlTypes.ROLE_DIALOG
    ROLE_MENU = controlTypes.ROLE_MENU
    ROLE_MENUBAR = controlTypes.ROLE_MENUBAR
    ROLE_MENUITEM = controlTypes.ROLE_MENUITEM
    ROLE_POPUPMENU = controlTypes.ROLE_POPUPMENU
    ROLE_CHECKMENUITEM = controlTypes.ROLE_CHECKMENUITEM
    ROLE_RADIOMENUITEM = controlTypes.ROLE_RADIOMENUITEM
    ROLE_TEAROFFMENU = controlTypes.ROLE_TEAROFFMENU
    ROLE_MENUBUTTON = controlTypes.ROLE_MENUBUTTON
    ROLE_TREEVIEW = controlTypes.ROLE_TREEVIEW
    ROLE_TOOLBAR = controlTypes.ROLE_TOOLBAR
    ROLE_BUTTON = controlTypes.ROLE_BUTTON
    ROLE_LINK = controlTypes.ROLE_LINK
    ROLE_GRAPHIC = controlTypes.ROLE_GRAPHIC
except AttributeError:
    ROLE_EDITABLETEXT = controlTypes.Role.EDITABLETEXT
    ROLE_PANE = controlTypes.Role.PANE
    ROLE_FRAME = controlTypes.Role.FRAME
    ROLE_DOCUMENT = controlTypes.Role.DOCUMENT
    ROLE_TAB = controlTypes.Role.TAB
    ROLE_TABCONTROL = controlTypes.Role.TABCONTROL
    ROLE_APPLICATION = controlTypes.Role.APPLICATION
    ROLE_DIALOG = controlTypes.Role.DIALOG
    ROLE_MENU = controlTypes.Role.MENU
    ROLE_MENUBAR = controlTypes.Role.MENUBAR
    ROLE_MENUITEM = controlTypes.Role.MENUITEM
    ROLE_POPUPMENU = controlTypes.Role.POPUPMENU
    ROLE_CHECKMENUITEM = controlTypes.Role.CHECKMENUITEM
    ROLE_RADIOMENUITEM = controlTypes.Role.RADIOMENUITEM
    ROLE_TEAROFFMENU = controlTypes.Role.TEAROFFMENU
    ROLE_MENUBUTTON = controlTypes.Role.MENUBUTTON
    ROLE_TREEVIEW = controlTypes.Role.TREEVIEW
    ROLE_TOOLBAR = controlTypes.Role.TOOLBAR
    ROLE_BUTTON = controlTypes.Role.BUTTON
    ROLE_LINK = controlTypes.Role.LINK
    ROLE_GRAPHIC = controlTypes.Role.GRAPHIC

