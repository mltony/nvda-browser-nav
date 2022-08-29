#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2022 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.
import api
import ctypes
import gui
import winUser

from .pywinsdk.relative import winsdk

def ephemeralCopyToClip(text: str):
    """
    Copies string to clipboard without leaving an entry in clipboard history.
    """
    with winUser.openClipboard(gui.mainFrame.Handle):
        winUser.emptyClipboard()
        winUser.setClipboardData(winUser.CF_UNICODETEXT, text)
        ephemeralFormat = ctypes.windll.user32.RegisterClipboardFormatW("ExcludeClipboardContentFromMonitorProcessing")
        ctypes.windll.user32.SetClipboardData(ephemeralFormat,None)

def ephemeralCopyToClipAndRestore(text: str):
    """
    Allows to copy string to clipboard so that the string can later be pasted to an application.
    This function will also restore previous state of clipboard on exit.
    This function doesn't leave trace in clipboard history.
    """
    try:
        oldClipboardValue = api.getClipData()
    except OSError as e:
        oldClipboardValue = ""
    ephemeralSetClipboard(text)
    try:
        yield
    finally:
        ephemeralSetClipboard(oldClipboardValue)
