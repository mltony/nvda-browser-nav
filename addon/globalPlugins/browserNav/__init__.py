#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

# This addon allows to navigate documents by indentation or offset level.
# In browsers you can navigate by object location on the screen.
# Author: Tony Malykh <anton.malykh@gmail.com>
# https://github.com/mltony/nvda-indent-nav/

import addonHandler
import api
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

from . addonConfig import *
from . beeper import *
from . import quickJump

import winsdk



debug = False
if debug:
    f = open("C:\\Users\\tmal\\drp\\1.txt", "w", encoding='utf-8')
def mylog(s):
    if debug:
        print(str(s), file=f)
        f.flush()


def myAssert(condition):
    if not condition:
        raise RuntimeError("Assertion failed")

try:
    REASON_CARET = controlTypes.REASON_CARET
except AttributeError:
    REASON_CARET = controlTypes.OutputReason.CARET



def pairUpOld(iterator):
    second = "Hello world!"
    while second is not None:
        try:
            first = iterator.__next__()
        except StopIteration:
            return
        try:
            second = iterator.__next__()
        except StopIteration:
            second = None
        yield first, second

def pairUp(l):
    for i in range(0, len(l), 2):
        try:
            yield (l[i], l[i+1])
        except IndexError:
            yield (l[i], None)
            return
def initConfiguration():
    confspec = {
        "crackleVolume" : "integer( default=25, min=0, max=100)",
        "beepVolume" : "integer( default=60, min=0, max=100)",
        "noNextTextChimeVolume" : "integer( default=50, min=0, max=100)",
        "noNextTextMessage" : "boolean( default=True)",
        "browserMode" : "integer( default=0, min=0, max=2)",
        "useFontFamily" : "boolean( default=True)",
        "useColor" : "boolean( default=True)",
        "useBackgroundColor" : "boolean( default=True)",
        "useBoldItalic" : "boolean( default=True)",
        "marks" : "string( default='(^upvote$|^up vote$)')",
        "skipEmptyParagraphs" : "boolean( default=True)",
        "skipEmptyLines" : "boolean( default=True)",
        "skipChimeVolume" : "integer( default=25, min=0, max=100)",
        "skipRegex" : "string( default='(^Hide or report this$)')",
        "tableNavigateToCell" : "boolean( default=True)",
    }
    config.conf.spec["browsernav"] = confspec

browseModeGestures = {
    "kb:NVDA+Alt+DownArrow" :"moveToNextSibling",
}



addonHandler.initTranslation()
initConfiguration()

class SettingsDialog(SettingsPanel):
    # Translators: Title for the settings dialog
    title = _("BrowserNav settings")

    def __init__(self, *args, **kwargs):
        super(SettingsDialog, self).__init__(*args, **kwargs)

    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
      # crackleVolumeSlider
        sizer=wx.BoxSizer(wx.HORIZONTAL)
        # Translators: volume of crackling slider
        label=wx.StaticText(self,wx.ID_ANY,label=_("Crackling volume"))
        slider=wx.Slider(self, wx.NewId(), minValue=0,maxValue=100)
        slider.SetValue(getConfig("crackleVolume"))
        sizer.Add(label)
        sizer.Add(slider)
        settingsSizer.Add(sizer)
        self.crackleVolumeSlider = slider
      # beep volume slider
        sizer=wx.BoxSizer(wx.HORIZONTAL)
        # Translators: volume of beeping  slider
        label=wx.StaticText(self,wx.ID_ANY,label=_("Beeping volume"))
        slider=wx.Slider(self, wx.NewId(), minValue=0,maxValue=100)
        slider.SetValue(getConfig("beepVolume"))
        sizer.Add(label)
        sizer.Add(slider)
        settingsSizer.Add(sizer)
        self.beepVolumeSlider = slider

      # noNextTextChimeVolumeSlider
        sizer=wx.BoxSizer(wx.HORIZONTAL)
        # Translators: End of document chime volume
        label=wx.StaticText(self,wx.ID_ANY,label=_("Volume of chime when no more sentences available"))
        slider=wx.Slider(self, wx.NewId(), minValue=0,maxValue=100)
        slider.SetValue(getConfig("noNextTextChimeVolume"))
        sizer.Add(label)
        sizer.Add(slider)
        settingsSizer.Add(sizer)
        self.noNextTextChimeVolumeSlider = slider

      # Checkboxes
        # Translators: Checkbox that controls spoken message when no next or previous text paragraph is available in the document
        label = _("Speak message when no next paragraph containing text available in the document")
        self.noNextTextMessageCheckbox = sHelper.addItem(wx.CheckBox(self, label=label))
        self.noNextTextMessageCheckbox.Value = getConfig("noNextTextMessage")

        # Translators: Checkbox that controls whether font family should be used for style
        label = _("Use font family for style")
        self.useFontFamilyCheckBox = sHelper.addItem(wx.CheckBox(self, label=label))
        self.useFontFamilyCheckBox.Value = getConfig("useFontFamily")

        # Translators: Checkbox that controls whether font color should be used for style
        label = _("Use font color for style")
        self.useColorCheckBox = sHelper.addItem(wx.CheckBox(self, label=label))
        self.useColorCheckBox.Value = getConfig("useColor")

        # Translators: Checkbox that controls whether background color should be used for style
        label = _("Use background color for style")
        self.useBackgroundColorCheckBox = sHelper.addItem(wx.CheckBox(self, label=label))
        self.useBackgroundColorCheckBox.Value = getConfig("useBackgroundColor")

        # Translators: Checkbox that controls whether bold and italic should be used for style
        label = _("Use bold and italic attributes for style")
        self.useBoldItalicCheckBox = sHelper.addItem(wx.CheckBox(self, label=label))
        self.useBoldItalicCheckBox.Value = getConfig("useBoldItalic")

        label = _("Jump to the first cell of the table when T or Shift+T is pressed.")
        self.tableNavigateToCellCheckBox = sHelper.addItem(wx.CheckBox(self, label=label))
        self.tableNavigateToCellCheckBox.Value = getConfig("tableNavigateToCell")



      # skipChimeVolumeSlider
        sizer=wx.BoxSizer(wx.HORIZONTAL)
        # Translators: volume of skip chime slider
        label=wx.StaticText(self,wx.ID_ANY,label=_("Volume of skipClutter chime"))
        slider=wx.Slider(self, wx.NewId(), minValue=0,maxValue=100)
        slider.SetValue(getConfig("skipChimeVolume"))
        sizer.Add(label)
        sizer.Add(slider)
        settingsSizer.Add(sizer)
        self.skipChimeVolumeSlider = slider


    def onSave(self):
        config.conf["browsernav"]["crackleVolume"] = self.crackleVolumeSlider.Value
        config.conf["browsernav"]["beepVolume"] = self.beepVolumeSlider.Value
        config.conf["browsernav"]["noNextTextChimeVolume"] = self.noNextTextChimeVolumeSlider.Value
        config.conf["browsernav"]["noNextTextMessage"] = self.noNextTextMessageCheckbox.Value
        config.conf["browsernav"]["useFontFamily"] = self.useFontFamilyCheckBox.Value
        config.conf["browsernav"]["useColor"] = self.useColorCheckBox.Value
        config.conf["browsernav"]["useBackgroundColor"] = self.useBackgroundColorCheckBox.Value
        config.conf["browsernav"]["useBoldItalic"] = self.useBoldItalicCheckBox.Value
        config.conf["browsernav"]["tableNavigateToCell"] = self.tableNavigateToCellCheckBox.Value
        config.conf["browsernav"]["skipChimeVolume"] = self.skipChimeVolumeSlider.Value


def getMode():
    return getConfig("browserMode")

# Browse mode constants:
BROWSE_MODES = [
    _("horizontal offset"),
    _("font size"),
    _("font size and same style"),
]

PARENT_OPERATORS = [operator.lt, operator.gt, operator.gt]
CHILD_OPERATORS = [operator.gt, operator.lt, operator.lt]
OPERATOR_STRINGS = {
    operator.lt: _("smaller"),
    operator.gt: _("greater"),
}
# Just some random unicode character that is not likely to appear anywhere.
# This character is used for semi-accessible jupyter edit box automation.
controlCharacter = "➉" # U+2789, Dingbat circled sans-serif digit ten

# This function is a fixed version of fromName function.
# As of v2020.3 it doesn't work correctly for gestures containing letters when the default locale on the computer is set to non-Latin, such as Russian.
import vkCodes
en_us_input_Hkl = 1033 + (1033 << 16)
def fromNameEnglish(name):
    """Create an instance given a key name.
    @param name: The key name.
    @type name: str
    @return: A gesture for the specified key.
    @rtype: L{KeyboardInputGesture}
    """
    keyNames = name.split("+")
    keys = []
    for keyName in keyNames:
        if keyName == "plus":
            # A key name can't include "+" except as a separator.
            keyName = "+"
        if keyName == keyboardHandler.VK_WIN:
            vk = winUser.VK_LWIN
            ext = False
        elif keyName.lower() == keyboardHandler.VK_NVDA.lower():
            vk, ext = keyboardHandler.getNVDAModifierKeys()[0]
        elif len(keyName) == 1:
            ext = False
            requiredMods, vk = winUser.VkKeyScanEx(keyName, en_us_input_Hkl)
            if requiredMods & 1:
                keys.append((winUser.VK_SHIFT, False))
            if requiredMods & 2:
                keys.append((winUser.VK_CONTROL, False))
            if requiredMods & 4:
                keys.append((winUser.VK_MENU, False))
            # Not sure whether we need to support the Hankaku modifier (& 8).
        else:
            vk, ext = vkCodes.byName[keyName.lower()]
            if ext is None:
                ext = False
        keys.append((vk, ext))

    if not keys:
        raise ValueError

    return keyboardHandler.KeyboardInputGesture(keys[:-1], vk, 0, ext)

def fromNameSmart(name):
    try:
        return keyboardHandler.KeyboardInputGesture.fromName(name)
    except:
        log.error(f"Couldn't resolve {name} keystroke using system default locale.", exc_info=True)
    try:
        return fromNameEnglish(name)
    except:
        log.error(f"Couldn't resolve {name} keystroke using English default locale.", exc_info=True)
    return None

kbdControlC = fromNameSmart("Control+c")
kbdControlV = fromNameSmart("Control+v")
kbdControlA = fromNameSmart("Control+a")
kbdControlHome = fromNameSmart("Control+Home")
kbdControlShiftHome = fromNameSmart("Control+Shift+Home")
kbdControlShiftDown = fromNameSmart("Control+Shift+DownArrow")
kbdShiftRight = fromNameSmart("Shift+RightArrow")
kbdControlEnd = fromNameSmart("Control+End")
kbdBackquote = fromNameSmart("`")
kbdDelete = fromNameSmart("Delete")
kbdLeft = fromNameSmart("LeftArrow")
kbdRight = fromNameSmart("RightArrow")
kbdUp = fromNameSmart("UpArrow")
kbdDown = fromNameSmart("DownArrow")

allModifiers = [
    winUser.VK_LCONTROL, winUser.VK_RCONTROL,
    winUser.VK_LSHIFT, winUser.VK_RSHIFT, winUser.VK_LMENU,
    winUser.VK_RMENU, winUser.VK_LWIN, winUser.VK_RWIN,
]

def executeAsynchronously(gen):
    """
    This function executes a generator-function in such a manner, that allows updates from the operating system to be processed during execution.
    For an example of such generator function, please see GlobalPlugin.script_editJupyter.
    Specifically, every time the generator function yilds a positive number,, the rest of the generator function will be executed
    from within wx.CallLater() call.
    If generator function yields a value of 0, then the rest of the generator function
    will be executed from within wx.CallAfter() call.
    This allows clear and simple expression of the logic inside the generator function, while still allowing NVDA to process update events from the operating system.
    Essentially the generator function will be paused every time it calls yield, then the updates will be processed by NVDA and then the remainder of generator function will continue executing.
    """
    if not isinstance(gen, types.GeneratorType):
        raise Exception("Generator function required")
    try:
        value = gen.__next__()
    except StopIteration:
        return
    l = lambda gen=gen: executeAsynchronously(gen)
    if value == 0:
        wx.CallAfter(l)
    else:
        wx.CallLater(value, l)

class NoSelectionError(Exception):
    def __init__(self, *args, **kwargs):
        super(NoSelectionError, self).__init__(*args, **kwargs)

class EditBoxUpdateError(Exception):
    def __init__(self, *args, **kwargs):
        super(EditBoxUpdateError, self).__init__(*args, **kwargs)



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
    def __init__(self, parent, text, cursorLine, cursorColumn, onTextComplete):
        self.tabValue = "    "
        # Translators: Title of calibration dialog
        title_string = _("Edit text")
        super(EditTextDialog, self).__init__(parent, title=title_string)
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
        self.textCtrl.Bind(wx.EVT_TEXT_PASTE, self.onClipboardPaste)
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
        mylog(f"vk={keyCode} a{alt} c{control} s{shift}")
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
                self.keystroke = fromNameSmart(keystrokeName)
                self.text = self.textCtrl.GetValue()
                curPos = self.textCtrl.GetInsertionPoint()
                dummy, columnNum, lineNum = self.textCtrl.PositionToXY(curPos)
                self.EndModal(wx.ID_OK)
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
            self.EndModal(wx.ID_CANCEL)
            hasChanged = self.text != self.originalText
            import globalVars
            globalVars.s1 = self.originalText
            globalVars.s2 = self.text
            wx.CallAfter(lambda: self.onTextComplete(wx.ID_CANCEL, self.text, hasChanged, lineNum, columnNum, None))
        event.Skip()

    def onClipboardPaste(self, event):
        s = api.getClipData()
        s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        api.copyToClip(s)
        event.Skip()

jupyterUpdateInProgress = False

originalExecuteGesture = None
blockBeeper = Beeper()
blockKeysUntil = 0
def preExecuteGesture(selfself, gesture, *args, **kwargs):
    global blockKeysUntil
    now = time.time()
    if now < blockKeysUntil:
        # Block this keystroke!
        blockBeeper.fancyBeep("DG#", length=100, left=50, right=50)
        return
    return originalExecuteGesture(selfself, gesture, *args, **kwargs)

def blockAllKeys(timeoutSeconds):
    global blockKeysUntil
    now = time.time()
    if blockKeysUntil > now:
        raise Exception("Keys are already blocked")
    blockKeysUntil =now  + timeoutSeconds
    beeper.fancyBeep("CDGA", length=int(1000 * timeoutSeconds), left=5, right=5)

def unblockAllKeys():
    global blockKeysUntil
    blockKeysUntil = 0
    beeper.stop()

def getSimpleHorizontalOffset(textInfo):
    try:
        obj = textInfo.NVDAObjectAtStart
        x = obj.location[0]
        return x
    except:
        return None

def getFontSize(textInfo, formatting):
    try:
        size =float( formatting["font-size"].replace("pt", ""))
        return size
    except:
        return 0

def extractRoles(textInfo):
    result = set()
    fields = textInfo.getTextWithFields()
    for field in fields:
        try:
            role = field.field['role']
        except:
            continue
        result.add(role)
    return result

def isRolePresent(textInfo, roles):
    formatConfig=config.conf['documentFormatting']
    fields = textInfo.getTextWithFields(formatConfig)
    for field in fields:
        try:
            role = field.field['role']
        except:
            continue
        if role in roles:
            return True
    return False
def getFormatting(info):
    formatField=textInfos.FormatField()
    formatConfig=config.conf['documentFormatting']
    for field in info.getTextWithFields(formatConfig):
        #if isinstance(field,textInfos.FieldCommand): and isinstance(field.field,textInfos.FormatField):
        try:
            formatField.update(field.field)
        except:
            pass
    return formatField

def getBeepTone(textInfo):
    mode = getConfig("browserMode")
    if mode == 0:
        offset = getSimpleHorizontalOffset(textInfo)
        width = api.getDesktopObject().location.right
        MAX_ALLOWED_OCTAVES = 3
        octave_pixels = width/MAX_ALLOWED_OCTAVES
        base_freq = speech.IDT_BASE_FREQUENCY
        tone = base_freq * (2 ** (offset/octave_pixels))
        return tone
    elif mode in [1,2]:
        size = getFontSize(textInfo, getFormatting(textInfo))
        # Larger fonts should map onto lower tones, so computing inverse here
        tone = 3000/size
        return tone
    else:
        raise Exception(f'Unknown mode {mode}')
lastTone = 0
lastTextInfo = None



def sonifyTextInfo(textInfo, oldTextInfo=None, includeCrackle=False):
    if textInfo is None:
        return
    return sonifyTextInfoImpl(textInfo, oldTextInfo, includeCrackle)
quickJump.sonifyTextInfo = sonifyTextInfo
def sonifyTextInfoImpl(textInfo, lastTextInfo, includeCrackle):
    w = lambda: scriptHandler.isScriptWaiting()
    beepVolume=getConfig("beepVolume")
    if beepVolume > 0:
        if w():return

        global lastTone
        try:
            tone = getBeepTone(textInfo)
        except:
            return
        tone = max(tone, 10)
        tone = min(tone, 20000)

        if tone != lastTone:
            tones.beep(tone, 50, left=beepVolume, right=beepVolume)
        lastTone = tone

    if (
        includeCrackle
        and lastTextInfo is not None
        and getConfig("crackleVolume") > 0
        and isinstance(textInfo, Gecko_ia2_TextInfo)
        and isinstance(lastTextInfo, Gecko_ia2_TextInfo)
        and lastTextInfo.obj == textInfo.obj
    ):
        if w():return
        lastTextInfo = lastTextInfo.copy()
        lastTextInfo.expand(textInfos.UNIT_PARAGRAPH)
        t1, t2 = textInfo, lastTextInfo
        if textInfo.compareEndPoints(lastTextInfo, 'startToStart') == 0:
            return
        if textInfo.compareEndPoints(lastTextInfo, 'startToStart') > 0:
            t1,t2 = t2,t1
        if False:
            # Old method, more precise, but seems to be causing a deadlock within NVDA with very low frequency - once every couple of days, so very difficult to debug
            span = t1.copy()
            span.setEndPoint(t2, 'endToEnd')
            if span._endOffset - span._startOffset > 100000:
                paragraphs = 50
            else:
                paragraphs = len(list(span.getTextInChunks(textInfos.UNIT_PARAGRAPH)))
        else:
            # new simplified way:
            paragraphs = (t2._endOffset - t1._startOffset) // 20
        paragraphs = max(0, paragraphs - 2)
        initialDelay = 0 if beepVolume==0 else 50
        beeper.simpleCrackle(paragraphs, volume=getConfig("crackleVolume"), initialDelay=initialDelay)

originalCaretMovementScriptHelper = None
originalQuickNavScript = None
originalTableScriptHelper = None
original_set_selection = None
def preCaretMovementScriptHelper(self, gesture,unit, direction=None,posConstant=textInfos.POSITION_SELECTION, *args, **kwargs):
    oldSelection = self.selection
    if (
        (
            (
                getConfig("skipEmptyParagraphs")
                and unit == textInfos.UNIT_PARAGRAPH
            ) or  (
                getConfig("skipEmptyLines")
                and unit == textInfos.UNIT_LINE
            )
        )
        and direction is not None
        and posConstant==textInfos.POSITION_SELECTION
        and not isinstance(self,textInfos.DocumentWithPageTurns)
        and not scriptHandler.willSayAllResume(gesture)
    ):
        quickJump.caretMovementWithAutoSkip(self, gesture,unit, direction,posConstant, *args, **kwargs)
    else:
        originalCaretMovementScriptHelper(self, gesture, unit, direction, posConstant, *args, **kwargs)
    if unit not in {textInfos.UNIT_CHARACTER, textInfos.UNIT_WORD}:
        sonifyTextInfo(self.selection)

def preQuickNavScript(self,gesture, itemType, direction, errorMessage, readUnit, *args, **kwargs):
    oldSelection = self.selection
    result = originalQuickNavScript(self,gesture, itemType, direction, errorMessage, readUnit, *args, **kwargs)
    if itemType == 'table' and getConfig("tableNavigateToCell"):
        info = self.selection.copy()
        info.collapse()
        info.expand(textInfos.UNIT_PARAGRAPH)
        roles = extractRoles(info)
        if (
            controlTypes.Role.TABLE in roles
            and controlTypes.Role.TABLECELL not in roles
            and controlTypes.Role.TABLECOLUMNHEADER not in roles
        ):
            info.move(textInfos.UNIT_PARAGRAPH, 1)
            info.expand(textInfos.UNIT_PARAGRAPH)
            roles = extractRoles(info)
            if (
                controlTypes.Role.TABLE in roles
                and (
                    controlTypes.Role.TABLECELL in roles
                    or controlTypes.Role.TABLECOLUMNHEADER in roles
                )
            ):
                self._set_selection(info, reason=controlTypes.OutputReason.QUICKNAV)
                speech.speakTextInfo(info, reason=controlTypes.OutputReason.QUICKNAV)

    sonifyTextInfo(self.selection, oldTextInfo=oldSelection, includeCrackle=True)
    return result

def preTableScriptHelper(self, *args, **kwargs):
    oldSelection = self.selection
    result = originalTableScriptHelper(self, *args, **kwargs)
    sonifyTextInfo(self.selection)
    return result

selectionHistory = {}
selectionHistoryLock = threading.Lock()
def purgeSelectionHistory():
    # Purge expired entries
    global selectionHistory
    selectionHistory = {
        k:v
        for k,v in selectionHistory.items()
        if k() is not None
    }
def pre_set_selection(self, info):
    try:
        sh = self.selectionHistory
    except AttributeError:
        sh = SelectionHistory()
        self.selectionHistory = sh
    sh.append(info)
    return original_set_selection(self, info)

class SelectionHistory:
    def __init__(self):
        self.entries = []
        self.ptr = -1

    def append(self, info):
        if not isinstance(info, Gecko_ia2_TextInfo):
            return
        try:
            del self.entries[self.ptr + 1:]
        except IndexError:
            pass
        info = info.copy()
        info.expand(textInfos.UNIT_PARAGRAPH)
        self.entries.append(info._startOffset)
        self.ptr = len(self.entries)

    def goBack(self, info):
        currentInfo = info.copy()
        currentInfo.expand(textInfos.UNIT_PARAGRAPH)
        historicalInfo = currentInfo.copy()
        while self.ptr > 0:
            self.ptr -= 1
            offset = self.entries[self.ptr]
            historicalInfo._startOffset = historicalInfo._endOffset = offset
            historicalInfo.expand(textInfos.UNIT_PARAGRAPH)
            if not currentInfo.isOverlapping(historicalInfo):
                return historicalInfo
        raise IndexError()


def browserNavPopup(selfself,gesture):
    self = selfself
    gui.mainFrame.prePopup()
    try:
        frame = wx.Frame(None, -1,"Fake popup frame", pos=(1, 1),size=(1, 1))
        menu = wx.Menu()
        menu.AppendMenu(wx.ID_ANY, '&Bookmark', quickJump.makeBookmarkSubmenu(self, frame))
        menu.AppendMenu(wx.ID_ANY, '&Website', quickJump.makeWebsiteSubmenu(self, frame))
        frame.Bind(
            wx.EVT_MENU_CLOSE,
            lambda evt: frame.Close()
        )
        frame.Show()

        wx.CallAfter(lambda: frame.PopupMenu(menu))
    finally:
        gui.mainFrame.postPopup()
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("BrowserNav")
    beeper = Beeper()

    def __init__(self, *args, **kwargs):
        super(GlobalPlugin, self).__init__(*args, **kwargs)
        self.createMenu()
        self.injectBrowseModeKeystrokes()
        self.lastJupyterText = ""
        global originalExecuteGesture, originalCaretMovementScriptHelper, originalQuickNavScript, originalTableScriptHelper, original_set_selection
        originalExecuteGesture = inputCore.InputManager.executeGesture
        inputCore.InputManager.executeGesture = preExecuteGesture
        originalCaretMovementScriptHelper = cursorManager.CursorManager._caretMovementScriptHelper
        cursorManager.CursorManager._caretMovementScriptHelper = preCaretMovementScriptHelper
        originalQuickNavScript = browseMode.BrowseModeTreeInterceptor._quickNavScript
        browseMode.BrowseModeTreeInterceptor._quickNavScript = preQuickNavScript
        originalTableScriptHelper = documentBase.DocumentWithTableNavigation._tableMovementScriptHelper
        documentBase.DocumentWithTableNavigation._tableMovementScriptHelper = preTableScriptHelper
        original_set_selection = cursorManager.CursorManager._set_selection
        cursorManager.CursorManager._set_selection = pre_set_selection
        editableText.EditableText.script_editInBrowserNav = lambda selfself, gesture: self.script_editJupyter(gesture, selfself)
        editableText.EditableText._EditableText__gestures['kb:NVDA+E'] = 'editInBrowserNav'
        quickJump.original_event_gainFocus = browseMode.BrowseModeDocumentTreeInterceptor.event_gainFocus
        browseMode.BrowseModeDocumentTreeInterceptor.event_gainFocus = quickJump.new_event_gainFocus
        quickJump.originalShouldPassThrough = browseMode.BrowseModeTreeInterceptor.shouldPassThrough
        browseMode.BrowseModeTreeInterceptor.shouldPassThrough = quickJump.newShouldPassThrough
        quickJump.original_event_treeInterceptor_gainFocus = browseMode.BrowseModeDocumentTreeInterceptor.event_treeInterceptor_gainFocus
        browseMode.BrowseModeDocumentTreeInterceptor.event_treeInterceptor_gainFocus = quickJump.pre_event_treeInterceptor_gainFocus
        quickJump.originalReportLiveRegion = NVDAHelper.nvdaControllerInternal_reportLiveRegion
        NVDAHelper.nvdaControllerInternal_reportLiveRegion = quickJump.newReportLiveRegion
        NVDAHelper._setDllFuncPointer(NVDAHelper.localLib,"_nvdaControllerInternal_reportLiveRegion", quickJump.newReportLiveRegion)




    def createMenu(self):
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(SettingsDialog)
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(quickJump.SettingsDialog)

    def terminate(self):
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(SettingsDialog)
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(quickJump.SettingsDialog)
        cursorManager.CursorManager._caretMovementScriptHelper = originalCaretMovementScriptHelper
        inputCore.InputManager.executeGesture = originalExecuteGesture
        browseMode.BrowseModeTreeInterceptor._quickNavScript = originalQuickNavScript
        documentBase.DocumentWithTableNavigation._tableMovementScriptHelper = originalTableScriptHelper
        cursorManager.CursorManager._set_selection = original_set_selection
        browseMode.BrowseModeDocumentTreeInterceptor.event_gainFocus = quickJump.original_event_gainFocus
        browseMode.BrowseModeTreeInterceptor.shouldPassThrough = quickJump.originalShouldPassThrough
        browseMode.BrowseModeDocumentTreeInterceptor.event_treeInterceptor_gainFocus = quickJump.original_event_treeInterceptor_gainFocus
        NVDAHelper.nvdaControllerInternal_reportLiveRegion = quickJump.originalReportLiveRegion
        NVDAHelper._setDllFuncPointer(NVDAHelper.localLib,"_nvdaControllerInternal_reportLiveRegion", quickJump.originalReportLiveRegion)


    def script_moveToNextSibling(self, gesture, selfself):
        mode = getMode()
        # Translators: error message if next sibling couldn't be found
        errorMessage = _("No next paragraph with the same {mode} in the document").format(
            mode=BROWSE_MODES[mode])
        self.moveInBrowser(1, errorMessage, operator.eq, selfself)

    def script_moveToPreviousSibling(self, gesture, selfself):
        mode = getMode()
        # Translators: error message if previous sibling couldn't be found
        errorMessage = _("No previous paragraph with the same {mode} in the document").format(
            mode=BROWSE_MODES[mode])
        self.moveInBrowser(-1, errorMessage, operator.eq, selfself)


    def script_moveToParent(self, gesture, selfself):
        mode = getMode()
        op = PARENT_OPERATORS[mode]
        # Translators: error message if parent could not be found
        errorMessage = _("No previous paragraph  with {qualifier} {mode} in the document").format(
            mode=BROWSE_MODES[mode],
            qualifier=OPERATOR_STRINGS[op])
        self.moveInBrowser(-1, errorMessage, op, selfself)

    def script_moveToNextParent(self, gesture, selfself):
        mode = getMode()
        op = PARENT_OPERATORS[mode]
        # Translators: error message if parent could not be found
        errorMessage = _("No next paragraph  with {qualifier} {mode} in the document").format(
            mode=BROWSE_MODES[mode],
            qualifier=OPERATOR_STRINGS[op])
        self.moveInBrowser(1, errorMessage, op, selfself)


    def script_moveToChild(self, gesture, selfself):
        mode = getMode()
        op = CHILD_OPERATORS[mode]
        # Translators: error message if child could not be found
        errorMessage = _("No next paragraph  with {qualifier} {mode} in the document").format(
            mode=BROWSE_MODES[mode],
            qualifier=OPERATOR_STRINGS[op])
        self.moveInBrowser(1, errorMessage, op, selfself)

    def script_moveToPreviousChild(self, gesture, selfself):
        mode = getMode()
        op = CHILD_OPERATORS[mode]
        # Translators: error message if child could not be found
        errorMessage = _("No previous paragraph  with {qualifier} {mode} in the document").format(
            mode=BROWSE_MODES[mode],
            qualifier=OPERATOR_STRINGS[op])
        self.moveInBrowser(-1, errorMessage, op, selfself)

    def script_rotor(self, gesture, selfself):
        mode = getMode()
        mode = (mode + 1) % len(BROWSE_MODES)
        setConfig("browserMode", mode)
        ui.message(_("BrowserNav navigates by ") + BROWSE_MODES[mode])

    def generateBrowseModeExtractors(self, selfself):
        textInfo = selfself.selection
        geckoMode = isinstance(textInfo, Gecko_ia2_TextInfo)
        #geckoMode = False
        if geckoMode:
            document = utils.getIA2Document(textInfo)
            documentHolder = utils.DocumentHolder(document)
        mode = getConfig("browserMode")
        if mode == 0:
            # horizontal offset
            extractFormattingFunc = lambda x: None
            if geckoMode:
                extractIndentFunc = lambda textInfo,x: utils.getGeckoParagraphIndent(textInfo, documentHolder)
            else:
                extractIndentFunc= lambda textInfo,x: getSimpleHorizontalOffset(textInfo)
            extractStyleFunc = lambda x,y: None
        elif mode in [1,2]:
            extractFormattingFunc = lambda textInfo: getFormatting(textInfo)
            extractIndentFunc = getFontSize
            if mode == 1:
                # Font size only
                extractStyleFunc = lambda textInfo, formatting: None
            else:
                # Both font fsize and style
                extractStyleFunc = lambda textInfo, formatting: self.formattingToStyle(formatting)
        return (
            extractFormattingFunc,
            extractIndentFunc,
            extractStyleFunc
        )

    def formattingToStyle(self, formatting):
        result = []
        if getConfig("useFontFamily"):
            result.append(formatting.get("font-family", None))
        if getConfig("useColor"):
            result.append(formatting.get("color", None))
        if getConfig("useBackgroundColor"):
            result.append(formatting.get("background-color", None))
        if getConfig("useBoldItalic"):
            result.append(formatting.get("bold", None))
            result.append(formatting.get("italic", None))
        return tuple(result)

    def moveInBrowser(self, increment, errorMessage, op, selfself):
        (
            extractFormattingFunc,
            extractIndentFunc,
            extractStyleFunc
        ) = self.generateBrowseModeExtractors(selfself)

        textInfo = selfself.selection.copy()
        textInfo.collapse()
        mylog(f"start: {textInfo.text}")
        textInfo.expand(textInfos.UNIT_PARAGRAPH)
        origFormatting = extractFormattingFunc(textInfo)
        origIndent = extractIndentFunc(textInfo, origFormatting)
        origStyle = extractStyleFunc(textInfo, origFormatting)
        mylog(f"origIndent={str(origIndent)}")
        distance = 0
        while True:
            result =textInfo.move(textInfos.UNIT_PARAGRAPH, increment)
            if result == 0:
                return endOfDocument(errorMessage)
            textInfo.expand(textInfos.UNIT_PARAGRAPH)
            text = textInfo.text
            if speech.isBlank(text):
                continue
            formatting = extractFormattingFunc(textInfo)
            indent = extractIndentFunc(textInfo, formatting)
            style = extractStyleFunc(textInfo, formatting)
            mylog(f'@{distance} text: {textInfo.text}')
            mylog(f'indent={str(indent)}')
            if style == origStyle:
                mylog("Styles math!")
                if op(indent, origIndent):
                    self.beeper.simpleCrackle(distance, volume=getConfig("crackleVolume"))
                    speech.speakTextInfo(textInfo, reason=REASON_CARET)
                    textInfo.collapse()
                    textInfo.updateCaret()
                    selfself.selection = textInfo
                    return
            distance += 1

    def findByRole(self, direction, roles, errorMessage, newMethod=False):
        focus = api.getFocusObject().treeInterceptor
        textInfo = focus.makeTextInfo(textInfos.POSITION_CARET)
        textInfo.expand(textInfos.UNIT_PARAGRAPH)
        distance = 0
        while True:
            distance += 1
            textInfo.collapse()
            result = textInfo.move(textInfos.UNIT_PARAGRAPH, direction)
            if result == 0:
                endOfDocument(errorMessage)
                return
            textInfo.expand(textInfos.UNIT_PARAGRAPH)
            if not newMethod:
                obj = textInfo.NVDAObjectAtStart
                testResult =  obj is not None and obj.role in roles
            else:
                testResult = isRolePresent(textInfo, roles)
            if testResult:
                textInfo.updateCaret()
                self.beeper.simpleCrackle(distance, volume=getConfig("crackleVolume"))
                speech.speakTextInfo(textInfo, reason=REASON_CARET)
                textInfo.collapse()
                focus._set_selection(textInfo)
                return

    def scrollToAll(self, direction, message):
        ui.message(message)
        focus = api.getFocusObject().treeInterceptor
        textInfo = focus.makeTextInfo(textInfos.POSITION_CARET)
        textInfo.expand(textInfos.UNIT_PARAGRAPH)
        textInfo.collapse()
        distance = 0
        while True:
            distance += 1
            #textInfo.collapse()
            result = textInfo.move(textInfos.UNIT_PARAGRAPH, direction)
            if result == 0:
                ui.message(_("Done."))
                return
            #textInfo.expand(textInfos.UNIT_PARAGRAPH)
            textInfo.NVDAObjectAtStart.scrollIntoView()

    #blacklistKeys = {"_startOfNode", "_endOfNode"}
    whitelistKeys = "color,font-family,font-size,bold,italic,strikethrough,underline".split(",")
    def compareFormatFields(self, f1, f2):
        if False:
          for key in set(f1.keys()).union(set(f2.keys())).difference(self.blacklistKeys):
            try:
                if f1[key] != f2[key]:
                    mylog(f"Inequality during comparison; key={key} f1={f1[key]} f2={f2[key]}")
                    return False
            except KeyError:
                mylog(f"KeyError during comparison; key={key} f1={key in f1} f2={key in f2}")
                return False
        for key in self.whitelistKeys:
            if key not in f1 and key not in f2:
                continue
            try:
                if f1[key] != f2[key]:
                    return False
            except KeyError:
                mylog(f"KeyError during comparison; key={key} f1={key in f1} f2={key in f2}")
                return False

        return True

    def findFormatChange(self, selfself, direction, errorMessage):
        mylog(f"findFormatChange direction={direction}")
        caretInfo = selfself.makeTextInfo(textInfos.POSITION_CARET)
        caretInfo.collapse()
        paragraphInfo = caretInfo.copy()
        paragraphInfo.expand(textInfos.UNIT_PARAGRAPH)
        textInfo = paragraphInfo.copy()
        paragraphInfo.collapse()
        textInfo.setEndPoint(caretInfo, 'startToStart' if direction > 0 else "endToEnd")
        formatConfig=config.conf['documentFormatting']
        formatInfo = caretInfo.copy()
        formatInfo.move(textInfos.UNIT_CHARACTER, 1, endPoint="end")
        fields = formatInfo.getTextWithFields(formatConfig)
        fields = [field
            for field in fields
            if (
                isinstance(field, textInfos.FieldCommand)
                and field.command == 'formatChange'
            )
        ]
        if len(fields) == 0:
            raise Exception("No formatting information available at the cursor!")
        originalFormat = fields[0]
        mylog(f"originalFormat={originalFormat}")
        while True:
            fields = textInfo.getTextWithFields(formatConfig)
            fields = [field
                for field in fields
                if (
                    isinstance(field, textInfos.FieldCommand)
                    and field.command == 'formatChange'
                )
                or isinstance(field, str)
            ]
            if len(fields) == 0:
                # This happens if curssor at the beginning of paragraph and we're moving back. Well, just go directly to the previous paragraph, nothing to do in this one.
                pass
            else:
                if not  isinstance(fields[0], textInfos.FieldCommand):
                    raise Exception("No formatting information found at cursor!")
                if not isinstance(fields[-1], str):
                    raise Exception("Formatting information found in the end - unexpected!")
                if direction < 0:
                    # First we swap the order of each format-string pair
                    # Second we invert the whole list
                    mylog("Inverting for backward search")
                    mylog(f"fields={fields}")
                    newFields = []
                    for (p1, p2) in pairUp([
                        (k, list(g))
                        for (k, g) in itertools.groupby(fields, key=type)
                    ]):
                        mylog(f"p2={p2}")
                        (k1, g1) = p1
                        g1 = list(g1)
                        mylog(f"p1={p1}")
                        mylog(f"g1={g1}")
                        if   k1 != textInfos.FieldCommand:
                            raise Exception("Corrupted order of format fields!")
                        if p2 is not None:
                            mylog("p2 is not None")
                            (k2, g2) = p2
                            if k2 != str:
                                raise Exception("Corrupted order of format fields!")
                            newFields.extend(list(g2)[::-1])
                            mylog("After extending g2")
                            mylog(str(newFields))
                        newFields.extend(list(g1)[::-1])
                        mylog("After extending g1")
                        mylog(str(newFields))

                    mylog("Before inversion")
                    mylog("\n".join(map(str, fields)))
                    fields = newFields[::-1]
                    mylog("After inversion")
                    mylog("\n".join(map(str, fields)))
                    mylog("###")

                adjustment = 0
                beginAdjustment = endAdjustment = None
                for field in fields:
                    if isinstance(field, textInfos.FieldCommand):
                        mylog(f"Field: {field}")
                        #if field != originalFormat:
                        if not self.compareFormatFields(field.field, originalFormat.field):
                            #Bingo! But we still need to keep going to find the end of that piece with different formatting
                            beginAdjustment = adjustment
                            mylog(f"beginAdjustment={beginAdjustment}")
                    elif isinstance(field, str):
                        mylog(f"'{field}'")
                        oldAdjustment = adjustment
                        adjustment += len(field)
                        mylog(f"old={oldAdjustment} adjustment={adjustment}")
                        if beginAdjustment is not None:
                            # Now really bingo!
                            endAdjustment = adjustment
                            mylog(f"endAdjustment={endAdjustment}")
                            break
                    else:
                        raise Exception("Impossible!")
                if beginAdjustment is not None:
                    # Found format change in this paragraph
                    if endAdjustment is None:
                        raise Exception("Found the beginning of format change, but failed to find the end!")
                    caretInfo.move(textInfos.UNIT_CHARACTER, direction * beginAdjustment)
                    caretInfo.move(textInfos.UNIT_CHARACTER, direction * (endAdjustment - beginAdjustment), endPoint="end" if direction > 0 else "start")
                    caretInfo.updateCaret()
                    selfself.selection = caretInfo
                    speech.speakTextInfo(caretInfo, reason=REASON_CARET)
                    return
            if True:
                # Now move to the next paragraph
                mylog("nextParagraph!")
                if direction < 0:
                    # If moving back, then position caret at the beginning of the following paragraph, since we'll be computing adjustment from the end
                    caretInfo = paragraphInfo.copy()
                result = paragraphInfo.move(textInfos.UNIT_PARAGRAPH, direction)
                if result == 0:
                    endOfDocument(_("No next format change!"))
                    return
                textInfo = paragraphInfo.copy()
                textInfo.expand(textInfos.UNIT_PARAGRAPH)
                mylog(f"paragraph: {textInfo.text}")
                if direction > 0:
                    caretInfo = paragraphInfo.copy()



    def findByControlField(self, direction, role, errorMessage):
        def getUniqueId(info):
            fields = info.getTextWithFields()
            for field in fields:
                if (
                    isinstance(field, textInfos.FieldCommand)
                    and field.command == "controlStart"
                    and "role" in field.field
                    and field.field['role'] == role
                ):
                    return field.field.get('uniqueID', 0)
            return None
        focus = api.getFocusObject().treeInterceptor
        textInfo = focus.makeTextInfo(textInfos.POSITION_CARET)
        textInfo.expand(textInfos.UNIT_PARAGRAPH)
        originalId = getUniqueId(textInfo)
        distance = 0
        while True:
            distance += 1
            textInfo.collapse()
            result = textInfo.move(textInfos.UNIT_PARAGRAPH, direction)
            if result == 0:
                endOfDocument(errorMessage)
                return
            textInfo.expand(textInfos.UNIT_PARAGRAPH)
            newId = getUniqueId(textInfo)
            if newId is not None and (newId != originalId):
                textInfo.updateCaret()
                self.beeper.simpleCrackle(distance, volume=getConfig("crackleVolume"))
                speech.speakTextInfo(textInfo, reason=REASON_CARET)
                textInfo.collapse()
                focus._set_selection(textInfo)
                return

    def script_editJupyter(self, gesture, selfself):
        global jupyterUpdateInProgress
        if jupyterUpdateInProgress:
            ui.message_("Jupyter cell update in progress!")
            self.beeper.fancyBeep("AF#", length=100, left=20, right=20)
            return
        fg=winUser.getForegroundWindow()
        if isinstance(selfself, editableText.EditableText):
            obj = selfself
        elif not config.conf["virtualBuffers"]["autoFocusFocusableElements"]:
            # We need to temporarily disable NVDA setting "Browse Mode > Automatic focus mode for focus changes"
            # Since we are going to focus current editable and don't want to enter focus mode.
            originalAutoPassThrough = config.conf["virtualBuffers"]["autoPassThroughOnFocusChange"]
            config.conf["virtualBuffers"]["autoPassThroughOnFocusChange"] = False
            with ExitStack() as stack:
                # return original value upon exiting this function
                # Actually sometimes focus events come in delayed, so we need to wait still a little longer, hence delaying for 1 second after exiting.
                def restoreAutoPassThrough():
                    config.conf["virtualBuffers"]["autoPassThroughOnFocusChange"] =             originalAutoPassThrough
                def restoreAutoPassThroughDelayed():
                    core.callLater(1000, restoreAutoPassThrough)
                stack.callback(restoreAutoPassThroughDelayed)

            selfself._focusLastFocusableObject()
            try:
                obj = selfself._lastFocusableObj
            except AttributeError:
                obj = selfself.currentFocusableNVDAObject
            timeout = time.time() + 2
            # Wait until the element we'd like to focus is actually focused
            while True:
                if time.time() > timeout:
                    raise EditBoxUpdateError(_("Timeout while trying to focus current edit box."))
                focus = api.getFocusObject()
                if obj.IA2UniqueID == focus.IA2UniqueID:
                    break
                time.sleep(10/1000) # sleep a bit to make sure that this object has properly focused
                api.processPendingEvents(processEventQueue=True)
        else:
            obj=selfself.currentNVDAObject
        if obj.role != ROLE_EDITABLETEXT:
            ui.message(_("Not editable"))
            return
        uniqueID = obj.IA2UniqueID
        self.startInjectingKeystrokes()
        try:
            kbdLeft.send()
            kbdRight.send()
            kbdControlShiftHome.send()
            preText = self.getSelection()
            kbdControlA.send()
            text = self.getSelection()
            kbdControlHome.send()
        except NoSelectionError as e:
            self.endInjectingKeystrokes()
            core.callLater(
                100,
                speech.speak,
                [_("Cannot copy text out of edit box. Please make sure edit box is not empty and not read-only!")],
            )
            raise e
        finally:
            self.endInjectingKeystrokes()
        if (len(text) == 0) or len(preText) == 0:
            ui.message("Failed to copy text from semi-accessible edit-box. Please make sure edit box is not empty.")
            return
        preLines = preText.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        cursorLine = len(preLines) - 1
        cursorColumn = len(preLines[-1])
        def getFocusObjectVerified():
                focus = api.getFocusObject()
                if focus.role != ROLE_EDITABLETEXT:
                    raise EditBoxUpdateError(_("Browser state has changed. Focused element is not an edit box. Role: %d.") % focus.role)
                if (uniqueID is not None) and (uniqueID != 0):
                    if uniqueID != focus.IA2UniqueID:
                        raise EditBoxUpdateError(_("Browser state has changed. Different element on the page is now focused."))
                return focus

        def makeVkInput(vkCodes):
            result = []
            if not isinstance(vkCodes, list):
                vkCodes = [vkCodes]
            for vk in vkCodes:
                input = winUser.Input(type=winUser.INPUT_KEYBOARD)
                input.ii.ki.wVk = vk
                result.append(input)
            for vk in reversed(vkCodes):
                input = winUser.Input(type=winUser.INPUT_KEYBOARD)
                input.ii.ki.wVk = vk
                input.ii.ki.dwFlags = winUser.KEYEVENTF_KEYUP
                result.append(input)
            return result

        def goToPosition(lineNum, columnNum):
            # This function is too slow for line numbers > 1000.
            # This is probably due to slow performance of Python's marshalling complex arguments to native Windows DLL
            # This is a good candidate to rewrite in a native code and supply in a tiny DLL file
            mylog(f"Pressing arrows to go to line={lineNum}, col={columnNum}")
            inputs = []
            inputs.extend(makeVkInput(winUser.VK_DOWN) * lineNum)
            inputs.extend(makeVkInput(winUser.VK_RIGHT) * columnNum)
            with keyboardHandler.ignoreInjection():
                winUser.SendInput(inputs)

        def updateText(result, text, hasChanged, cursorLine, cursorColumn, keystroke):
            mylog(f"hasChanged={hasChanged}")
            global jupyterUpdateInProgress
            jupyterUpdateInProgress = True
            self.lastJupyterText = text
            timeoutSeconds = 5
            timeout = time.time() + timeoutSeconds
            blockAllKeys(timeoutSeconds)
            try:
              # step 1. wait for all modifiers to be released
                while True:
                    if time.time() > timeout:
                        raise EditBoxUpdateError(_("Timed out during release modifiers stage"))
                    status = [
                        winUser.getKeyState(k) & 32768
                        for k in allModifiers
                    ]
                    if not any(status):
                        break
                    yield 1
              # Step 2: switch back to that browser window
                while  winUser.getForegroundWindow() != fg:
                    if time.time() > timeout:
                        raise EditBoxUpdateError(_("Timed out during switch to browser window stage"))
                    winUser.setForegroundWindow(fg)
                    winUser.setFocus(fg)
                    yield 1
              # Step 2.1: Ensure that the browser window is fully focused.
                # This is needed sometimes for Firefox - switching to it takes hundreds of milliseconds, especially when jupyter cells are large.
                obj.setFocus()
                #step21timeout = time.time() + 1 # Leave 1 second for this step
                goodCounter = 0
                roles = []
                kbdControlHome.send()
                while True:
                    if time.time() > timeout:
                        raise EditBoxUpdateError(_("Timed out during switch to window stage"))
                    focus = api.getFocusObject()
                    roles.append(focus.role)
                    if focus.role in [
                        ROLE_PANE,
                        ROLE_FRAME,
                        ROLE_DOCUMENT,
                    ]:
                        # All good, Firefox is burning cpu, keep sleeping!
                        yield 10
                        goodCounter = 0
                        continue
                    elif focus.role == ROLE_EDITABLETEXT:
                        goodCounter += 1
                        if goodCounter > 10:
                            tones.beep(1000, 100)
                            break
                        yield 10
                    else:
                        raise EditBoxUpdateError(_("Error during switch to window stage, focused element role is %d") % focus.role)

              # Step 3: start sending keys
                self.startInjectingKeystrokes()
                try:
                    shortTextMode = len(text) < 5
                  # Step 3.1. Select all and paste
                    if hasChanged:
                        self.copyToClip(text)
                        kbdControlA.send()
                        kbdControlV.send()
                  # Step 3.2. Select first character and copy to clip and wait to assure that edit box has processed the previous paste
                    if  hasChanged and not shortTextMode:
                        kbdControlHome.send()
                        kbdShiftRight.send()
                        kbdControlC.send()
                  # Step 3.3: Position cursor to synchronize with edit text window cursor
                    kbdControlHome.send()
                    goToPosition(cursorLine, cursorColumn)
                  # Step 3.4: Wait for clipbord to be updated to make sure we can flush clipboard
                    if  hasChanged and not shortTextMode:
                        while True:
                            yield 1
                            if time.time() > timeout:
                                raise EditBoxUpdateError(_("Timed out during single-character control+C stage"))
                            try:
                                newText = api.getClipData()
                            except PermissionError:
                                continue
                            if text != newText:
                                break
                    else:
                        # For very short texts just sleep a bit longer
                        yield 100
                finally:
                  # Step 3.3. Sleep for a bit more just to make sure things have propagated - in short text mode only.
                  # Apparently if we don't sleep, then either the previous value with ` would be used sometimes,
                  # or it will paste the original contents of clipboard.
                    if  hasChanged and shortTextMode:
                        core.callLater(
                            500,
                            self.endInjectingKeystrokes
                        )
                    else:
                        self.endInjectingKeystrokes()
              # Step 4: send the original keystroke, e.g. Control+Enter
                if keystroke is not None:
                    keystroke.send()

            except EditBoxUpdateError as e:
                tones.player.stop()
                unblockAllKeys()
                jupyterUpdateInProgress = False
                self.copyToClip(text)
                message = ("BrowserNav failed to update edit box.")
                message += "\n" + str(e)
                message += "\n" + _("Last edited text has been copied to the clipboard.")
                gui.messageBox(message)
            finally:
                unblockAllKeys()
                jupyterUpdateInProgress = False

        self.popupEditTextDialog(
            text, cursorLine, cursorColumn,
            lambda result, text, hasChanged, cursorLine, cursorColumn, keystroke: executeAsynchronously(updateText(result, text, hasChanged, cursorLine, cursorColumn, keystroke))
        )

    def script_copyJupyterText(self, gesture, selfself):
        if len(self.lastJupyterText) > 0:
            self.copyToClip(self.lastJupyterText)
            ui.message(_("Last Jupyter text has been copied to clipboard."))
        else:
            ui.message(_("No last Jupyter text., or last Jupyter text is empty."))

    def startInjectingKeystrokes(self):
        self.restoreKeyboardState()
        try:
            self.clipboardBackup = api.getClipData()
        except OSError as e:
            core.callLater(
                100,
                speech.speak,
                [_("Failed to read clipboard data. Please make sure clipboard is not empty - copy some text to clipboard.")],
            )
            raise e

    def endInjectingKeystrokes(self):
        self.copyToClip(self.clipboardBackup)

    def restoreKeyboardState(self):
        """
        Most likely this class is called from within a gesture. This means that Some of the modifiers, like
        Shift, Control, Alt are pressed at the moment.
        We need to virtually release them in order to send other keystrokes to VSCode.
        """
        modifiers = [winUser.VK_LCONTROL, winUser.VK_RCONTROL,
            winUser.VK_LSHIFT, winUser.VK_RSHIFT, winUser.VK_LMENU,
            winUser.VK_RMENU, winUser.VK_LWIN, winUser.VK_RWIN, ]
        for k in modifiers:
            if winUser.getKeyState(k) & 32768:
                winUser.keybd_event(k, 0, 2, 0)

    def copyToClip(self, text):
        lastException = None
        for i in range(10):
            try:
                api.copyToClip(text)
                return
            except PermissionError as e:
                lastException = e
                wx.Yield()
                continue
        raise Exception(lastException)

    def getSelection(self):
        self.copyToClip(controlCharacter)
        t0 = time.time()
        timeout = t0+3
        lastControlCTimestamp = 0
        while True:
            if time.time() - lastControlCTimestamp > 1:
                lastControlCTimestamp = time.time()
                kbdControlC.send()
            if time.time() > timeout:
                raise NoSelectionError("Time out while trying to copy data out of application.")

            try:
                data = api.getClipData()
                if data != controlCharacter:
                    return data
            except PermissionError:
                pass
            wx.Yield()
            time.sleep(10/1000)

    def popupEditTextDialog(self, text, cursorLine, cursorColumn, onTextComplete):
        gui.mainFrame.prePopup()
        d = EditTextDialog(gui.mainFrame, text, cursorLine, cursorColumn, onTextComplete)
        result = d.Show()
        gui.mainFrame.postPopup()

    def script_toggleOption(self, gesture, selfself, option, messages):
        setConfig(option, not getConfig(option))
        message = messages[int(getConfig(option))]
        ui.message(message)

    def script_goBack(self, gesture, selfself):
        try:
            sh = selfself.selectionHistory
        except AttributeError:
            endOfDocument(_("No cursor history available"))
            return
        try:
            info = sh.goBack(selfself.selection)
        except  IndexError:
            endOfDocument(_("Cannot go back any more"))
            return
        expandInfo = info.copy()
        expandInfo.expand(textInfos.UNIT_PARAGRAPH)
        speech.speakTextInfo(expandInfo, unit=textInfos.UNIT_PARAGRAPH, reason=REASON_CARET)
        original_set_selection(selfself, info)

    def injectBrowseModeKeystroke(self, keystrokes, funcName, script=None, doc=None):
        gp = self
        cls = browseMode.BrowseModeTreeInterceptor
        scriptFuncName = "script_" + funcName
        if script is None:
            gpFunc = getattr(gp, scriptFuncName)
            script = lambda selfself, gesture: gpFunc(gesture, selfself)
        script.__name__ = scriptFuncName
        script.category = "BrowserNav"
        if doc is not None:
            script.__doc__ = doc
        setattr(cls, scriptFuncName, script)
        if not isinstance(keystrokes, list):
            keystrokes = [keystrokes]
        for keystroke in keystrokes:
            cls._BrowseModeTreeInterceptor__gestures[keystroke] = funcName

    def injectBrowseModeKeystrokes(self):
      # Indentation navigation
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Alt+DownArrow",
            "moveToNextSibling",
            doc=_("Moves to next sibling in browser"))
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Alt+UpArrow",
            "moveToPreviousSibling",
            doc=_("Moves to previous sibling in browser"))
        self.injectBrowseModeKeystroke(
            ["kb:NVDA+Alt+LeftArrow", "kb:NVDA+Alt+Home"],
            "moveToParent",
            doc=_("Moves to next parent in browser"))
        self.injectBrowseModeKeystroke(
            ["kb:NVDA+Control+Alt+LeftArrow", "kb:NVDA+Alt+End"],
            "moveToNextParent",
            doc=_("Moves to next parent in browser"))
        self.injectBrowseModeKeystroke(
            ["kb:NVDA+Alt+RightArrow", "kb:NVDA+Alt+PageDown"],
            "moveToChild",
            doc=_("Moves to next child in browser"))
        self.injectBrowseModeKeystroke(
            ["kb:NVDA+Control+Alt+RightArrow", "kb:NVDA+Alt+PageUp"],
            "moveToPreviousChild",
            doc=_("Moves to previous child in browser"))
      #Rotor
        self.injectBrowseModeKeystroke(
            "kb:NVDA+O",
            "rotor",
            doc=_("Adjusts BrowserNav rotor"))

      # QuickJump 1 bookmarks
        self.injectBrowseModeKeystroke(
            "kb:J",
            "quickJumpForward",
            script=lambda selfself, gesture: quickJump.quickJump(selfself, gesture, quickJump.BookmarkCategory.QUICK_JUMP, 1,  _("No next QuickJump result. To configure QuickJump rules, please go to BrowserNav settings in NVDA configuration window.")),
            doc=_("QuickJump forward according to BrowserNav QuickJump bookmarks; please check browserNav configuration panel for the list of bookmarks."))
        self.injectBrowseModeKeystroke(
            "kb:Shift+J",
            "quickJumpBack",
            script=lambda selfself, gesture: quickJump.quickJump(selfself, gesture, quickJump.BookmarkCategory.QUICK_JUMP, -1,  _("No next QuickJump result. To configure QuickJump rules, please go to BrowserNav settings in NVDA configuration window.")),
            doc=_("QuickJump back according to BrowserNav QuickJump bookmarks; please check browserNav configuration panel for the list of bookmarks."))
      # QuickJump 2 and 3 bookmarks
        self.injectBrowseModeKeystroke(
            [],
            "quickJump2Forward",
            script=lambda selfself, gesture: quickJump.quickJump(selfself, gesture, quickJump.BookmarkCategory.QUICK_JUMP_2, 1,  _("No next QuickJump result for QuickJump2 bookmarks. To configure QuickJump rules, please go to BrowserNav settings in NVDA configuration window.")),
            doc=_("QuickJump forward according to BrowserNav QuickJump2 bookmarks; please check browserNav configuration panel for the list of bookmarks."))
        self.injectBrowseModeKeystroke(
            [],
            "quickJump2Back",
            script=lambda selfself, gesture: quickJump.quickJump(selfself, gesture, quickJump.BookmarkCategory.QUICK_JUMP_2, -1,  _("No next QuickJump result for QuickJump2 bookmarks. To configure QuickJump rules, please go to BrowserNav settings in NVDA configuration window.")),
            doc=_("QuickJump back according to BrowserNav QuickJump2 bookmarks; please check browserNav configuration panel for the list of bookmarks."))
        self.injectBrowseModeKeystroke(
            [],
            "quickJump3Forward",
            script=lambda selfself, gesture: quickJump.quickJump(selfself, gesture, quickJump.BookmarkCategory.QUICK_JUMP_3, 1,  _("No next QuickJump result for QuickJump3 bookmarks. To configure QuickJump rules, please go to BrowserNav settings in NVDA configuration window.")),
            doc=_("QuickJump forward according to BrowserNav QuickJump3 bookmarks; please check browserNav configuration panel for the list of bookmarks."))
        self.injectBrowseModeKeystroke(
            [],
            "quickJump3Back",
            script=lambda selfself, gesture: quickJump.quickJump(selfself, gesture, quickJump.BookmarkCategory.QUICK_JUMP_3, -1,  _("No next QuickJump result for QuickJump3 bookmarks. To configure QuickJump rules, please go to BrowserNav settings in NVDA configuration window.")),
            doc=_("QuickJump back according to BrowserNav QuickJump3 bookmarks; please check browserNav configuration panel for the list of bookmarks."))

      # AutoClick
        self.injectBrowseModeKeystroke(
            "kb:Alt+J",
            "autoClick",
            script=lambda selfself, gesture: quickJump.autoClick(selfself, gesture, quickJump.BookmarkCategory.QUICK_CLICK),
            doc=_("AutoClick  according to BrowserNav AutoClick bookmark; please check browserNav configuration panel for the list of bookmarks."))
        self.injectBrowseModeKeystroke(
            [],
            "autoClick2",
            script=lambda selfself, gesture: quickJump.autoClick(selfself, gesture, quickJump.BookmarkCategory.QUICK_CLICK_2),
            doc=_("AutoClick  according to BrowserNav AutoClick2 bookmark; please check browserNav configuration panel for the list of bookmarks."))
        self.injectBrowseModeKeystroke(
            [],
            "autoClick3",
            script=lambda selfself, gesture: quickJump.autoClick(selfself, gesture, quickJump.BookmarkCategory.QUICK_CLICK_3),
            doc=_("AutoClick  according to BrowserNav AutoClick3 bookmark; please check browserNav configuration panel for the list of bookmarks."))
      # Hierarchical
        for letter in "`1234567890":
            try:
                level = int(letter)
                if level == 0:
                    level = 10
                levelStr = _("at level {level}").format(level=level)
            except ValueError:
                level = None
                levelStr = ""
            self.injectBrowseModeKeystroke(
                f"kb:Alt+{letter}",
                f"hierarchicalQuickJumpForward{level}",
                script=lambda selfself, gesture, level=level, levelStr=levelStr: quickJump.hierarchicalQuickJump(
                    selfself,
                    gesture,
                    quickJump.BookmarkCategory.HIERARCHICAL,
                    direction=1,
                    level=level - 1 if level is not None else None,
                    unbounded=False,
                    errorMsg=_("No next hierarchical bookmark {levelStr}").format(levelStr=levelStr)
                ),
                doc=_("Jump to next hierarchical bookmark {levelStr}; please check browserNav configuration panel for hierarchical bookmark configuration.").format(
                    levelStr=levelStr
                ))
            self.injectBrowseModeKeystroke(
                f"kb:Alt+Shift+{letter}",
                f"hierarchicalQuickJumpBack{level}",
                script=lambda selfself, gesture, level=level, levelStr=levelStr: quickJump.hierarchicalQuickJump(
                    selfself,
                    gesture,
                    quickJump.BookmarkCategory.HIERARCHICAL,
                    direction=-1,
                    level=level - 1 if level is not None else None,
                    unbounded=False,
                    errorMsg=_("No previous hierarchical bookmark {levelStr}").format(levelStr=levelStr)
                ),
                doc=_("Jump to previous hierarchical bookmark {levelStr}; please check browserNav configuration panel for hierarchical bookmark configuration.").format(
                    levelStr=levelStr
                ))
      # Tabs
        # Example page with tabs:
        # https://wet-boew.github.io/v4.0-ci/demos/tabs/tabs-en.html
        self.injectBrowseModeKeystroke(
            "kb:Y",
            "nextTab",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles={ROLE_TAB, ROLE_TABCONTROL},
                errorMessage=_("No next tab"),
                newMethod=True,
            ),
            doc=_("Jump to next tab"))
        self.injectBrowseModeKeystroke(
            "kb:Shift+Y",
            "previousTab",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles={ROLE_TAB, ROLE_TABCONTROL},
                errorMessage=_("No previous tab"),
                newMethod=True,
            ),
            doc=_("Jump to previous tab"))

      #Dialog
        dialogTypes = [ROLE_APPLICATION, ROLE_DIALOG]
        self.injectBrowseModeKeystroke(
            "kb:P",
            "nextDialog",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles=dialogTypes,
                errorMessage=_("No next dialog")),
            doc=_("Jump to next dialog"))
        self.injectBrowseModeKeystroke(
            "kb:Shift+P",
            "previousDialog",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=dialogTypes,
                errorMessage=_("No previous dialog")),
            doc=_("Jump to previous dialog"))
      # Menus
        menuTypes = [
            ROLE_MENU,
            ROLE_MENUBAR,
            ROLE_MENUITEM,
            ROLE_POPUPMENU,
            ROLE_CHECKMENUITEM,
            ROLE_RADIOMENUITEM,
            ROLE_TEAROFFMENU,
            ROLE_MENUBUTTON,
        ]
        self.injectBrowseModeKeystroke(
            "kb:Z",
            "nextMenu",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles=menuTypes,
                errorMessage=_("No next menu"),
                newMethod=True,
            ),
            doc=_("Jump to next menu"))
        self.injectBrowseModeKeystroke(
            "kb:Shift+Z",
            "previousMenu",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=menuTypes,
                errorMessage=_("No previous menu"),
                newMethod=True,
            ),
            doc=_("Jump to previous menu"))

      # Tree views, tool bars
        self.injectBrowseModeKeystroke(
            "kb:0",
            "nextTreeView",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles=[ROLE_TREEVIEW],
                errorMessage=_("No next tree view")),
            doc=_("Jump to next tree view"))
        self.injectBrowseModeKeystroke(
            "kb:Shift+0",
            "previousTreeView",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=[ROLE_TREEVIEW],
                errorMessage=_("No previous tree view")),
            doc=_("Jump to previous tree view"))
        self.injectBrowseModeKeystroke(
            "kb:9",
            "nextToolBar",
            script=lambda selfself, gesture: self.findByControlField(
                direction=1,
                role=ROLE_TOOLBAR,
                errorMessage=_("No next tool bar")),
            doc=_("Jump to next tool bar"))
        self.injectBrowseModeKeystroke(
            "kb:Shift+9",
            "previousToolBar",
            script=lambda selfself, gesture: self.findByControlField(
                direction=-1,
                role=ROLE_TOOLBAR,
                errorMessage=_("No previous tool bar")),
            doc=_("Jump to previous tool bar"))
      #Format change
        self.injectBrowseModeKeystroke(
            "kb:`",
            "nextFormatChange",
            script=lambda selfself, gesture: self.findFormatChange(
                selfself,
                direction=1,
                errorMessage=_("No next format change")),
            doc=_("Jump to next format change"))
        self.injectBrowseModeKeystroke(
            "kb:Shift+`",
            "previousFormatChange",
            script=lambda selfself, gesture: self.findFormatChange(
                selfself,
                direction=-1,
                errorMessage=_("No previous format change")),
            doc=_("Jump to previous format change"))
      # Scroll all:
        self.injectBrowseModeKeystroke(
            "kb:\\",
            "scrollAllForward",
            script=lambda selfself, gesture: self.scrollToAll(
                direction=1,
                message=_("Scrolling forward. This may load more elements on the page.")),
            doc=_("Scroll to all possible elements forward"))
        self.injectBrowseModeKeystroke(
            "kb:Shift+\\",
            "scrollAllBackward",
            script=lambda selfself, gesture: self.scrollToAll(
                direction=-1,
                message=_("Scrolling backward. This may load more elements on the page.")),
            doc=_("Scroll to all possible elements backward"))

      # Edit Jupyter
        self.injectBrowseModeKeystroke(
            "kb:NVDA+E",
            "editJupyter",
            script=lambda selfself, gesture: self.script_editJupyter(gesture, selfself),
            doc=_("Edit semi-accessible edit box."))
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Control+E",
            "copyJupyterText",
            script=lambda selfself, gesture: self.script_copyJupyterText(gesture, selfself),
            doc=_("Copy the last text from semi-accessible edit box to clipboard."))
      # Toggle skip clutter
        self.injectBrowseModeKeystroke(
            "kb:Control+/",
            "toggleSkipEmptyParagraphs",
            script=lambda selfself, gesture: self.script_toggleOption(
                gesture,
                selfself,
                "skipEmptyParagraphs",
                [
                    _("Skip clutter off for paragraph navigation"),
                    _("Skip clutter on for paragraph navigation"),
                ]
            ),
            doc=_("Toggle skip clutter for paragraph navigation"))
        self.injectBrowseModeKeystroke(
            "kb:/",
            "toggleSkipEmptyLines",
            script=lambda selfself, gesture: self.script_toggleOption(
                gesture,
                selfself,
                "skipEmptyLines",
                [
                    _("Skip clutter off for line navigation"),
                    _("Skip clutter on for line navigation"),
                ]
            ),
            doc=_("Toggle skip clutter for line navigation"))
      # Go back in browse mode
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Shift+LeftArrow",
            "goBack",
            script=lambda selfself, gesture: self.script_goBack(
                gesture,
                selfself,
            ),
            doc=_("Experimental: go back to the previous location of cursor in current document"))
        self.injectBrowseModeKeystroke(
            "kb:NVDA+J",
            "browserNavPopup",
            script=lambda selfself, gesture: browserNavPopup(
                selfself,
                gesture,
            ),
            doc=_("Show BrowserNav popup menu."))




