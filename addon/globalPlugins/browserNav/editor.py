#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2022 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

# This addon allows to navigate documents by indentation or offset level.
# In browsers you can navigate by object location on the screen.
# Author: Tony Malykh <anton.malykh@gmail.com>
# https://github.com/mltony/nvda-indent-nav/

import addonHandler
import api
from . beeper import *
import browseMode
from contextlib import ExitStack
import controlTypes
import config
from . constants import *
import core
import ctypes
import cursorManager
import documentBase
import editableText
import functools
import globalPluginHandler
import gui
from gui.settingsDialogs import SettingsPanel
import inputCore
import itertools
import keyboardHandler
from logHandler import log
import math
import nvwave
import NVDAHelper
import operator
import os
import re
import scriptHandler
from scriptHandler import script
import speech
import struct
import sys
import textInfos
import threading
import time
import tones
import types
import ui
from . import utils
from virtualBuffers.gecko_ia2 import Gecko_ia2_TextInfo
import wave
import weakref
import winUser
import wx
from wx.stc import StyledTextCtrl
from . import clipboard
class GoToLineDialog(wx.Dialog):
    def __init__(self, parent, lineNum):
        # Translators: Title of Go To Line dialog
        title_string = _("Go to line")
        super(GoToLineDialog, self).__init__(parent, title=title_string)
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        #sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.lineNumEdit = gui.guiHelper.LabeledControlHelper(self, _("Go to line:"), wx.TextCtrl).control
        self.lineNumEdit.Value = str(lineNum)
        sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))
        self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
        self.lineNumEdit.SetFocus()
        self.lineNumEdit.SetSelection(-1,-1)

    def onOk(self, evt):
        strVal = self.lineNumEdit.Value
        try:
            result = int(strVal)
            if result <= 0:
                raise ValueError()
            self.result = result
        except ValueError:
            gui.messageBox(_("Line number must be a positive integer!"),
                _("Wrong line number"),
                style=wx.OK |  wx.CENTER | wx.ICON_ERROR
            )
            self.lineNumEdit.SetFocus()
            self.lineNumEdit.SetSelection(-1,-1)
            return
        self.EndModal(wx.ID_OK)

lastRegexSearch = ""
class RegexSearchDialog(wx.Dialog):
    def __init__(self, parent):
        title_string = _("Regex search")
        super(RegexSearchDialog, self).__init__(parent, title=title_string)
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        self.strEdit = gui.guiHelper.LabeledControlHelper(self, _("Go to line:"), wx.TextCtrl).control
        self.strEdit.Value = lastRegexSearch
        sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))
        self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
        self.strEdit.SetFocus()

    def onOk(self, evt):
        strVal = self.strEdit.Value
        try:
            r = re.compile(strVal)
        except re.error:
            gui.messageBox(_("Invalid regular expression"),
                _("Wrong regex"),
                style=wx.OK |  wx.CENTER | wx.ICON_ERROR
            )
            self.strEdit.SetFocus()
            return
        self.EndModal(wx.ID_OK)
        global lastRegexSearch
        lastRegexSearch = strVal



class EditTextDialog(wx.Dialog):
    def __init__(self, parent, text, cursorLine, cursorColumn, onTextComplete, title=None):
        self.tabValue = "    "
        if title is None:
            # Translators: Title of calibration dialog
            title = _("Edit text")
        super(EditTextDialog, self).__init__(parent, title=title)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        self.text = text
        self.originalText = text
        self.onTextComplete = onTextComplete
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

        self.textCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
        # We have to use plain text ctrl and implement some functionality.
        # I wish I could use StyledTextCtrl, but as of July 2021 it doesn't appear to be accessible with NVDA, even though it is based on Scintilla.
        #self.textCtrl = StyledTextCtrl(self, style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
        self.textCtrl.Bind(wx.EVT_CHAR, self.onChar)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyUP)
        self.textCtrl.Bind(wx.EVT_TEXT_PASTE, self.onClipboardPaste2)
        sHelper.addItem(self.textCtrl)
        self.textCtrl.SetValue(text)
        self.SetFocus()
        self.Maximize(True)
        pos = self.textCtrl.XYToPosition(cursorColumn, cursorLine)
        self.textCtrl.SetInsertionPoint(pos)
        # There seems to be a bug in wxPython textCtrl, when cursor is not set to the right line. To workaround calling it again in 1 ms.
        core.callLater(1, self.textCtrl.SetInsertionPoint, pos)


    def onGoTo(self, event):
        curPos = self.textCtrl.GetInsertionPoint()
        dummy, columnNum, lineNum = self.textCtrl.PositionToXY(curPos)
        d = GoToLineDialog(self, lineNum + 1)
        result = d.ShowModal()
        if result == wx.ID_OK:
            lineNum = d.result - 1
            pos = self.textCtrl.XYToPosition(0, lineNum)
            self.textCtrl.SetInsertionPoint(pos)

    def onFind(self, event):
        d = RegexSearchDialog(self)
        result = d.ShowModal()
        if result == wx.ID_OK:
            self.doFind(1)

    def doFind(self, direction):
        cursorPos = self.textCtrl.GetInsertionPoint()
        allText = self.textCtrl.GetRange(0, -1)
        preText = self.textCtrl.GetRange( 0, cursorPos)
        allText = allText.replace("\r\n", "\n").replace("\r", "\n")
        preText = preText.replace("\r\n", "\n").replace("\r", "\n")
        r = re.compile(lastRegexSearch, re.IGNORECASE)
        matches = list(re.finditer(r, allText))
        if direction > 0:
            matches = [m for m in matches if m.start(0) > len(preText)]
        else:
            matches = [m for m in matches if m.end(0) <= len(preText)]
        if len(matches) == 0:
            endOfDocument(_("No match!"))
            return
        mindex = 0 if direction > 0 else -1
        match = matches[mindex]
        preMatch = allText[:match.start(0)]
        preMatchLines = preMatch.split("\n")
        pos = self.textCtrl.XYToPosition(len(preMatchLines[-1]), len(preMatchLines) - 1)
        self.textCtrl.SetInsertionPoint(pos)

    def reindent(self, string, direction):
        if direction > 0:
            return self.tabValue + string
        if string.startswith(self.tabValue):
            return string[len(self.tabValue):]
        return string.lstrip(" ")

    def onChar(self, event):
        control = event.ControlDown()
        shift = event.ShiftDown()
        alt = event.AltDown()
        keyCode = event.GetKeyCode ()
        #mylog(f"vk={keyCode} a{alt} c{control} s{shift}")
        if event.GetKeyCode() in [10, 13]:
            # 13 means Enter
            # 10 means Control+Enter
            modifiers = [
                control, shift, alt
            ]
            if not any(modifiers):
                # Just pure enter without any modifiers
                # Perform Autoindent
                curPos = self.textCtrl.GetInsertionPoint
                lineNum = len(self.textCtrl.GetRange( 0, self.textCtrl.GetInsertionPoint() ).split("\n")) - 1
                lineText = self.textCtrl.GetLineText(lineNum)
                m = re.search("^\s*", lineText)
                if m:
                    self.textCtrl.WriteText("\n" + m.group(0))
                else:
                    self.textCtrl.WriteText("\n")
            else:
                modifierNames = [
                    "control",
                    "shift",
                    "alt",
                ]
                modifierTokens = [
                    modifierNames[i]
                    for i in range(len(modifiers))
                    if modifiers[i]
                ]
                keystrokeName = "+".join(modifierTokens + ["Enter"])
                self.keystroke = keyboardHandler.KeyboardInputGesture.fromName(keystrokeName)
                self.text = self.textCtrl.GetValue()
                curPos = self.textCtrl.GetInsertionPoint()
                dummy, columnNum, lineNum = self.textCtrl.PositionToXY(curPos)
                self.Close()
                hasChanged = self.text != self.originalText
                wx.CallAfter(lambda: self.onTextComplete(wx.ID_OK, self.text, hasChanged, lineNum, columnNum, self.keystroke))
        elif event.GetKeyCode() == wx.WXK_TAB:
            if alt or control:
                event.Skip()
            else:
                pos1, pos2 = self.textCtrl.GetSelection()
                if pos1 == pos2 and not shift:
                    self.textCtrl.WriteText(self.tabValue)
                elif pos1 == pos2 and shift:
                    # Shift+Tab
                    curPos = self.textCtrl.GetInsertionPoint()
                    dummy, curCol, curLine = self.textCtrl.PositionToXY(curPos)
                    beginLinePos = self.textCtrl.XYToPosition(0, curLine)
                    allText = self.textCtrl.Value
                    allText = allText.replace("\r\n", "\n").replace("\r", "\n")
                    allLines = allText.split("\n")
                    lineStr = allLines[curLine]
                    preLine = lineStr[:curCol]
                    if preLine.endswith(self.tabValue):
                        newCurCol = curCol - len(self.tabValue)
                        lineStr = lineStr[:newCurCol] + lineStr[curCol:]
                        allLines[curLine] = lineStr
                        allText = "\n".join(allLines)
                        self.textCtrl.Value = allText
                        pos = self.textCtrl.XYToPosition(newCurCol, curLine)
                        self.textCtrl.SetInsertionPoint(pos)

                else:
                    allText = self.textCtrl.Value
                    allText = allText.replace("\r\n", "\n").replace("\r", "\n")
                    allLines = allText.split("\n")
                    dummy, col1, line1 = self.textCtrl.PositionToXY(pos1)
                    dummy, col2, line2 = self.textCtrl.PositionToXY(pos2)
                    if col2 == 0 and line2 > line1:
                        line2 -= 1
                    for index in range(line1, line2+1):
                        allLines[index]  = self.reindent(allLines[index], -1 if  shift else 1)
                    allText = "\n".join(allLines)
                    self.textCtrl.Value = allText
                    pos1 = self.textCtrl.XYToPosition(0, line1)
                    pos2 = self.textCtrl.XYToPosition(0, line2 + 1)
                    self.textCtrl.SetSelection(pos1, pos2)
        elif event.GetKeyCode() == 1:
            # Control+A
            self.textCtrl.SetSelection(-1,-1)
        elif event.GetKeyCode() == wx.WXK_HOME:
            if not any([control, shift, alt]):
                curPos = self.textCtrl.GetInsertionPoint()
                #lineNum = len(self.textCtrl.GetRange( 0, self.textCtrl.GetInsertionPoint() ).split("\n")) - 1
                #colNum = len(self.textCtrl.GetRange( 0, self.textCtrl.GetInsertionPoint() ).split("\n")[-1])
                _, colNum,lineNum = self.textCtrl.PositionToXY(self.textCtrl.GetInsertionPoint())
                lineText = self.textCtrl.GetLineText(lineNum)
                m = re.search("^\s*", lineText)
                if not m:
                    raise Exception("This regular expression must match always.")
                indent = len(m.group(0))
                if indent == colNum:
                    newColNum = 0
                else:
                    newColNum = indent
                newPos = self.textCtrl.XYToPosition(newColNum, lineNum)
                self.textCtrl.SetInsertionPoint(newPos)
            else:
                event.Skip()
        elif  event.GetKeyCode() == 7:
            # Control+G
            self.onGoTo(event)
        elif  event.GetKeyCode() == 6:
            # Control+F
            self.onFind(event)
        elif event.GetKeyCode() == 342:
            # F3 or Shift+F3
            if not alt and not control:
                direction = 1 if not shift else -1
                self.doFind(direction)
            else:
                event.Skip()

        else:
            event.Skip()


    def OnKeyUP(self, event):
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_ESCAPE:
            self.text = self.textCtrl.GetValue()
            curPos = self.textCtrl.GetInsertionPoint()
            dummy, columnNum, lineNum = self.textCtrl.PositionToXY(curPos)
            self.Close()
            hasChanged = self.text != self.originalText
            #import globalVars
            #globalVars.s1 = self.originalText
            #globalVars.s2 = self.text
            wx.CallAfter(lambda: self.onTextComplete(wx.ID_CANCEL, self.text, hasChanged, lineNum, columnNum, None))
        event.Skip()

    def onClipboardPasteOld(self, event):
        # With this function Control+V works unreliably. In 1-2% of cases it fails to paste, and failiure rate sometimes spikes up to 50%.
        # I haven't been able to figure out why.
        s = api.getClipData()
        s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        api.copyToClip(s)
        event.Skip()
    
    def onClipboardPasteExperimental(self, event):
        def updateLineEndings():
            text = self.textCtrl.GetValue()
            caretOffset = self.textCtrl.GetInsertionPoint()
            caretOffsetFromEnd = len(text) - caretOffset
            text = re.sub(r'(?<!\r)\n', '\r\n', text)
            self.textCtrl.SetValue(text)
            newCaretOffset = len(text) - caretOffsetFromEnd
            self.textCtrl.SetInsertionPoint(newCaretOffset)
        core.callLater(10, updateLineEndings)
        tones.beep(500, 50)
        event.Skip()

    def onClipboardPaste2(self, event):
        s = api.getClipData()
        originalClipboardText = s
        s = re.sub(r'(?<!\r)\n', '\r\n', s)
        clipboard.ephemeralCopyToClip(s)
        time.sleep(0.1)
        event.Skip()
        core.callLater(300, clipboard.ephemeralCopyToClip, originalClipboardText)
