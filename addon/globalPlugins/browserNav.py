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
import controlTypes
import config
import core
import ctypes
import cursorManager
import documentBase
import functools
import globalPluginHandler
import gui
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
import textInfos
import threading
import time
import tones
import types
import ui
from virtualBuffers.gecko_ia2 import Gecko_ia2_TextInfo
import wave
import weakref
import winUser
import wx

debug = False
if debug:
    f = open("C:\\Users\\tony\\Dropbox\\2.txt", "w")
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
    }
    config.conf.spec["browsernav"] = confspec

browseModeGestures = {
    "kb:NVDA+Alt+DownArrow" :"moveToNextSibling",
}

def getConfig(key):
    value = config.conf["browsernav"][key]
    return value

def setConfig(key, value):
    config.conf["browsernav"][key] = value


addonHandler.initTranslation()
initConfiguration()

class SettingsDialog(gui.SettingsDialog):
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
      # BrowserMarks regexp text edit
        self.marksEdit = gui.guiHelper.LabeledControlHelper(self, _("Browser marks regexp"), wx.TextCtrl).control
        self.marksEdit.Value = getConfig("marks")

      # Skipping over empty paragraphs
        # Translators: Checkbox that controls whether we should skip over empty paragraphs
        label = _("Skip over empty paragraphs (unless in form fields)")
        self.skipEmptyParagraphsCheckbox = sHelper.addItem(wx.CheckBox(self, label=label))
        self.skipEmptyParagraphsCheckbox.Value = getConfig("skipEmptyParagraphs")

        # Translators: Checkbox that controls whether we should skip over empty lines
        label = _("Skip over empty lines (unless in form fields)")
        self.skipEmptyLinesCheckbox = sHelper.addItem(wx.CheckBox(self, label=label))
        self.skipEmptyLinesCheckbox.Value = getConfig("skipEmptyLines")
      # skipChimeVolumeSlider
        sizer=wx.BoxSizer(wx.HORIZONTAL)
        # Translators: volume of skip chime slider
        label=wx.StaticText(self,wx.ID_ANY,label=_("Volume of skip paragraph chime"))
        slider=wx.Slider(self, wx.NewId(), minValue=0,maxValue=100)
        slider.SetValue(getConfig("skipChimeVolume"))
        sizer.Add(label)
        sizer.Add(slider)
        settingsSizer.Add(sizer)
        self.skipChimeVolumeSlider = slider
      # Skip regexp text edit
        self.skipRegexEdit = gui.guiHelper.LabeledControlHelper(self, _("Also skip over paragraphs that match regex:"), wx.TextCtrl).control
        self.skipRegexEdit.Value = getConfig("skipRegex")


    def onOk(self, evt):
        config.conf["browsernav"]["crackleVolume"] = self.crackleVolumeSlider.Value
        config.conf["browsernav"]["beepVolume"] = self.beepVolumeSlider.Value
        config.conf["browsernav"]["noNextTextChimeVolume"] = self.noNextTextChimeVolumeSlider.Value
        config.conf["browsernav"]["noNextTextMessage"] = self.noNextTextMessageCheckbox.Value
        config.conf["browsernav"]["useFontFamily"] = self.useFontFamilyCheckBox.Value
        config.conf["browsernav"]["useColor"] = self.useColorCheckBox.Value
        config.conf["browsernav"]["useBackgroundColor"] = self.useBackgroundColorCheckBox.Value
        config.conf["browsernav"]["useBoldItalic"] = self.useBoldItalicCheckBox.Value
        config.conf["browsernav"]["marks"] = self.marksEdit.Value
        config.conf["browsernav"]["skipEmptyParagraphs"] = self.skipEmptyParagraphsCheckbox.Value
        config.conf["browsernav"]["skipEmptyLines"] = self.skipEmptyLinesCheckbox.Value
        config.conf["browsernav"]["skipChimeVolume"] = self.skipChimeVolumeSlider.Value
        config.conf["browsernav"]["skipRegex"] = self.skipRegexEdit.Value
        super(SettingsDialog, self).onOk(evt)


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
kbdControlShiftDown = fromNameSmart("Control+Shift+DownArrow")
kbdControlEnd = fromNameSmart("Control+End")
kbdBackquote = fromNameSmart("`")
kbdDelete = fromNameSmart("Delete")

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

class EditBoxUpdateError(Exception):
    def __init__(self, *args, **kwargs):
        super(EditBoxUpdateError, self).__init__(*args, **kwargs)

class Beeper:
    BASE_FREQ = speech.IDT_BASE_FREQUENCY
    def getPitch(self, indent):
        return self.BASE_FREQ*2**(indent/24.0) #24 quarter tones per octave.

    BEEP_LEN = 10 # millis
    PAUSE_LEN = 5 # millis
    MAX_CRACKLE_LEN = 400 # millis
    #MAX_BEEP_COUNT = MAX_CRACKLE_LEN // (BEEP_LEN + PAUSE_LEN)
    MAX_BEEP_COUNT = 40 # Corresponds to about 500 paragraphs with the log formula

    def __init__(self):
        self.player = nvwave.WavePlayer(
            channels=2,
            samplesPerSec=int(tones.SAMPLE_RATE),
            bitsPerSample=16,
            outputDevice=config.conf["speech"]["outputDevice"],
            wantDucking=False
        )



    def fancyCrackle(self, levels, volume, initialDelay=0):
        l = len(levels)
        coef = 10
        l = coef * math.log(
            1 + l/coef
        )
        l = int(round(l))
        levels = self.uniformSample(levels, min(l, self.MAX_BEEP_COUNT ))
        beepLen = self.BEEP_LEN
        pauseLen = self.PAUSE_LEN
        initialDelaySize = 0 if initialDelay == 0 else NVDAHelper.generateBeep(None,self.BASE_FREQ,initialDelay,0, 0)
        pauseBufSize = NVDAHelper.generateBeep(None,self.BASE_FREQ,pauseLen,0, 0)
        beepBufSizes = [NVDAHelper.generateBeep(None,self.getPitch(l), beepLen, volume, volume) for l in levels]
        bufSize = initialDelaySize + sum(beepBufSizes) + len(levels) * pauseBufSize
        buf = ctypes.create_string_buffer(bufSize)
        bufPtr = 0
        bufPtr += initialDelaySize
        for l in levels:
            bufPtr += NVDAHelper.generateBeep(
                ctypes.cast(ctypes.byref(buf, bufPtr), ctypes.POINTER(ctypes.c_char)),
                self.getPitch(l), beepLen, volume, volume)
            bufPtr += pauseBufSize # add a short pause
        self.player.stop()
        self.player.feed(buf.raw)

    def simpleCrackle(self, n, volume, initialDelay=0):
        return self.fancyCrackle([0] * n, volume, initialDelay=initialDelay)


    NOTES = "A,B,H,C,C#,D,D#,E,F,F#,G,G#".split(",")
    NOTE_RE = re.compile("[A-H][#]?")
    BASE_FREQ = 220
    def getChordFrequencies(self, chord):
        myAssert(len(self.NOTES) == 12)
        prev = -1
        result = []
        for m in self.NOTE_RE.finditer(chord):
            s = m.group()
            i =self.NOTES.index(s)
            while i < prev:
                i += 12
            result.append(int(self.BASE_FREQ * (2 ** (i / 12.0))))
            prev = i
        return result

    def fancyBeep(self, chord, length, left=10, right=10):
        beepLen = length
        freqs = self.getChordFrequencies(chord)
        intSize = 8 # bytes
        bufSize = max([NVDAHelper.generateBeep(None,freq, beepLen, right, left) for freq in freqs])
        if bufSize % intSize != 0:
            bufSize += intSize
            bufSize -= (bufSize % intSize)
        self.player.stop()
        bbs = []
        result = [0] * (bufSize//intSize)
        for freq in freqs:
            buf = ctypes.create_string_buffer(bufSize)
            NVDAHelper.generateBeep(buf, freq, beepLen, right, left)
            bytes = bytearray(buf)
            unpacked = struct.unpack("<%dQ" % (bufSize // intSize), bytes)
            result = map(operator.add, result, unpacked)
        maxInt = 1 << (8 * intSize)
        result = map(lambda x : x %maxInt, result)
        packed = struct.pack("<%dQ" % (bufSize // intSize), *result)
        self.player.feed(packed)

    def uniformSample(self, a, m):
        n = len(a)
        if n <= m:
            return a
        # Here assume n > m
        result = []
        for i in range(0, m*n, n):
            result.append(a[i  // m])
        return result
    def stop(self):
        self.player.stop()

class EditTextDialog(wx.Dialog):
    def __init__(self, parent, text, onTextComplete):
        self.tabValue = "    "
        # Translators: Title of calibration dialog
        title_string = _("Edit text")
        super(EditTextDialog, self).__init__(parent, title=title_string)
        self.text = text
        self.onTextComplete = onTextComplete
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

        self.textCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
        self.textCtrl.Bind(wx.EVT_CHAR, self.onChar)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyUP)
        sHelper.addItem(self.textCtrl)
        self.textCtrl.SetValue(text)
        self.SetFocus()
        self.Maximize(True)

    def onChar(self, event):
        control = event.ControlDown()
        shift = event.ShiftDown()
        alt = event.AltDown()
        keyCode = event.GetKeyCode()
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
                self.EndModal(wx.ID_OK)
                wx.CallAfter(lambda: self.onTextComplete(wx.ID_OK, self.text, self.keystroke))
        elif event.GetKeyCode() == wx.WXK_TAB:
            if alt or control:
                event.Skip()
            elif not shift:
                # Just Tab
                self.textCtrl.WriteText(self.tabValue)
            else:
                # Shift+Tab
                curPos = self.textCtrl.GetInsertionPoint()
                lineNum = len(self.textCtrl.GetRange( 0, self.textCtrl.GetInsertionPoint() ).split("\n")) - 1
                priorText = self.textCtrl.GetRange( 0, self.textCtrl.GetInsertionPoint() )
                text = self.textCtrl.GetValue()
                postText = text[len(priorText):]
                if priorText.endswith(self.tabValue):
                    newText = priorText[:-len(self.tabValue)] + postText
                    self.textCtrl.SetValue(newText)
                    self.textCtrl.SetInsertionPoint(curPos - len(self.tabValue))
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
        else:
            event.Skip()


    def OnKeyUP(self, event):
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_ESCAPE:
            self.text = self.textCtrl.GetValue()
            self.EndModal(wx.ID_CANCEL)
            wx.CallAfter(lambda: self.onTextComplete(wx.ID_CANCEL, self.text, None))
        event.Skip()

jupyterUpdateInProgress = False

originalExecuteGesture = None
beeper = Beeper()
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

def getHorizontalOffset(textInfo):
    obj = textInfo.NVDAObjectAtStart
    x = obj.location[0]
    for i in range(1000):
        obj = obj.parent
        if obj is None:
            return x
        if obj.role == controlTypes.ROLE_DOCUMENT:
            return x - obj.location[0]
    raise Exception('Infinitely many parents!')

def getFontSize(textInfo, formatting):
    try:
        size =float( formatting["font-size"].replace("pt", ""))
        return size
    except:
        return 0

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
        offset = getHorizontalOffset(textInfo)
        octave_pixels = 500
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
beeper = Beeper()
def sonifyTextInfo(textInfo, oldTextInfo=None, includeCrackle=False):
    if textInfo is None:
        return
    return sonifyTextInfoImpl(textInfo, oldTextInfo, includeCrackle)
def sonifyTextInfoImpl(textInfo, lastTextInfo, includeCrackle):
    #w = lambda: api.processPendingEvents(processEventQueue=False) or scriptHandler.isScriptWaiting()
    w = lambda: scriptHandler.isScriptWaiting()
    beepVolume=getConfig("beepVolume")
    if beepVolume > 0:
        if w():return

        global lastTone
        #textInfo = textInfo.copy()
        #textInfo.expand(textInfos.UNIT_PARAGRAPH)
        try:
            tone = getBeepTone(textInfo)
        except:
            return

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
            paragraphs = (t2._endOffset - t1._startOffset) // 10
        paragraphs = max(0, paragraphs - 2)
        initialDelay = 0 if beepVolume==0 else 50
        beeper.simpleCrackle(paragraphs, volume=getConfig("crackleVolume"), initialDelay=initialDelay)

def getSoundsPath():
    globalPluginPath = os.path.abspath(os.path.dirname(__file__))
    addonPath = os.path.split(globalPluginPath)[0]
    soundsPath = os.path.join(addonPath, "sounds")
    return soundsPath

@functools.lru_cache(maxsize=128)
def adjustVolume(bb, volume):
    # Assuming bb is encoded 116 bits per value!
    n = len(bb) // 2
    format = f"<{n}h"
    unpacked = struct.unpack(format, bb)
    unpacked = [int(x * volume / 100) for x in unpacked]
    result=  struct.pack(format, *unpacked)
    return result
    if False:
        bb = list(bb)
        for i in range(0, len(bb), 2):
            x = bb[i] + (bb[i+1] << 8)
            x = int(x * volume / 100)
            bb[i] = x & 0xFF
            x >>= 8
            bb[i + 1] = x & 0xFF
        return bytes(bb)

spcFile=None
spcPlayer=None
spcBuf = None
def skippedParagraphChime():
    global spcFile, spcPlayer, spcBuf
    if spcPlayer is  None:
        spcFile = wave.open(getSoundsPath() + "\\on.wav","r")
        spcPlayer = nvwave.WavePlayer(channels=spcFile.getnchannels(), samplesPerSec=spcFile.getframerate(),bitsPerSample=spcFile.getsampwidth()*8, outputDevice=config.conf["speech"]["outputDevice"],wantDucking=False)
        spcFile.rewind()
        spcFile.setpos(100 *         spcFile.getframerate() // 1000)
        spcBuf = spcFile.readframes(spcFile.getnframes())
    def playSkipParagraphChime():
        spcPlayer.stop()
        spcPlayer.feed(
            adjustVolume(
                spcBuf,
                getConfig("skipChimeVolume")
            )
        )
        spcPlayer.idle()
    threading.Thread(target=playSkipParagraphChime).start()


NON_SKIPPABLE_ROLES = {
    controlTypes.ROLE_CHECKBOX,
    controlTypes.ROLE_RADIOBUTTON,
    controlTypes.ROLE_EDITABLETEXT,
    controlTypes.ROLE_BUTTON,
    controlTypes.ROLE_MENUBAR,
    controlTypes.ROLE_MENUITEM,
    controlTypes.ROLE_POPUPMENU,
    controlTypes.ROLE_COMBOBOX,
    controlTypes.ROLE_LIST,
    controlTypes.ROLE_LISTITEM,
    controlTypes.ROLE_HELPBALLOON,
    controlTypes.ROLE_TOOLTIP,
    controlTypes.ROLE_LINK,
    controlTypes.ROLE_TREEVIEW,
    controlTypes.ROLE_TREEVIEWITEM,
    controlTypes.ROLE_TAB,
    controlTypes.ROLE_TABCONTROL,
    controlTypes.ROLE_SLIDER,
    controlTypes.ROLE_PROGRESSBAR,
    controlTypes.ROLE_SCROLLBAR,
    controlTypes.ROLE_STATUSBAR,
    controlTypes.ROLE_DROPDOWNBUTTON,
    controlTypes.ROLE_FORM,
    controlTypes.ROLE_APPLICATION,
    controlTypes.ROLE_GROUPING,
    controlTypes.ROLE_CHECKMENUITEM,
    controlTypes.ROLE_DATEEDITOR,
    controlTypes.ROLE_DIRECTORYPANE,
    controlTypes.ROLE_RADIOMENUITEM,
    controlTypes.ROLE_EDITBAR,
    controlTypes.ROLE_TERMINAL,
    controlTypes.ROLE_RICHEDIT,
    controlTypes.ROLE_RULER,
    controlTypes.ROLE_TOGGLEBUTTON,
    controlTypes.ROLE_CARET,
    controlTypes.ROLE_DROPLIST,
    controlTypes.ROLE_SPLITBUTTON,
    controlTypes.ROLE_MENUBUTTON,
    controlTypes.ROLE_DROPDOWNBUTTONGRID,
    controlTypes.ROLE_MATH,
    controlTypes.ROLE_HOTKEYFIELD,
    controlTypes.ROLE_INDICATOR,
    controlTypes.ROLE_SPINBUTTON,
    controlTypes.ROLE_SOUND,
    controlTypes.ROLE_TREEVIEWBUTTON,
    controlTypes.ROLE_IPADDRESS,
    controlTypes.ROLE_FILECHOOSER,
    controlTypes.ROLE_MENU,
    controlTypes.ROLE_PASSWORDEDIT,
    controlTypes.ROLE_FONTCHOOSER,
}

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
        skipRe = re.compile(getConfig("skipRegex"))
        skipped = False
        oldInfo=self.makeTextInfo(posConstant)
        info=oldInfo.copy()
        info.collapse(end=self.isTextSelectionAnchoredAtStart)
        if self.isTextSelectionAnchoredAtStart and not oldInfo.isCollapsed:
            info.move(textInfos.UNIT_CHARACTER,-1)
        info.expand(unit)
        text = info.text
        info.collapse()
        for i in range(10):
            result = info.move(unit,direction)
            if result == 0:
                break
            expandInfo = info.copy()
            expandInfo.expand(unit)
            expandText = expandInfo.text
            if skipRe.search(expandText):
                skipped = True
                continue
            fields=expandInfo.getTextWithFields() or []
            roles = {field.field['role'] for field in fields if hasattr(field, 'field') and field.field is not None and 'role' in field.field}
            if len(roles.intersection(NON_SKIPPABLE_ROLES)) > 0:
                mylog("Roles don't match!")
                inter = roles.intersection(NON_SKIPPABLE_ROLES)
                s = ",".join([controlTypes.roleLabels[r] for r in inter])
                mylog(s)
                break
            if not speech.isBlank(expandText):
                mylog("Speech is not blank!")
                break
            skipped = True

        selection = info.copy()
        info.expand(unit)
        speech.speakTextInfo(info, unit=unit, reason=REASON_CARET)
        if not oldInfo.isCollapsed:
            speech.speakSelectionChange(oldInfo, selection)
        self.selection = selection
        if skipped:
            skippedParagraphChime()
    else:
        originalCaretMovementScriptHelper(self, gesture, unit, direction, posConstant, *args, **kwargs)
    if unit not in {textInfos.UNIT_CHARACTER, textInfos.UNIT_WORD}:
        sonifyTextInfo(self.selection)

def preQuickNavScript(self, *args, **kwargs):
    oldSelection = self.selection
    result = originalQuickNavScript(self, *args, **kwargs)
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
    key = weakref.ref(self)
    with selectionHistoryLock:
        purgeSelectionHistory()
        if key not in selectionHistory:
            selectionHistory[key] = SelectionHistory()
        sh = selectionHistory[key]
        sh.append(info)
    return original_set_selection(self, info)

class SelectionHistory:
    def __init__(self):
        self.entries = []
        self.ptr = -1

    def append(self, info):
        try:
            del self.entries[self.ptr + 1:]
        except IndexError:
            pass
        info = info.copy()
        info.expand(textInfos.UNIT_PARAGRAPH)
        self.entries.append(info)
        self.ptr = len(self.entries)
        
    def goBack(self, info):
        info = info.copy()
        info.expand(textInfos.UNIT_PARAGRAPH)
        while self.ptr > 0:
            self.ptr -= 1
            if not info.isOverlapping(self.entries[self.ptr]):
                return self.entries[self.ptr]
        raise IndexError()


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


    def createMenu(self):
        def _popupMenu(evt):
            gui.mainFrame._popupSettingsDialog(SettingsDialog)
        self.prefsMenuItem  = gui.mainFrame.sysTrayIcon.preferencesMenu.Append(wx.ID_ANY, _("BrowserNav..."))
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, _popupMenu, self.prefsMenuItem)

    def terminate(self):
        prefMenu = gui.mainFrame.sysTrayIcon.preferencesMenu
        prefMenu.Remove(self.prefsMenuItem)
        cursorManager.CursorManager._caretMovementScriptHelper = originalCaretMovementScriptHelper
        inputCore.InputManager.executeGesture = originalExecuteGesture
        browseMode.BrowseModeTreeInterceptor._quickNavScript = originalQuickNavScript
        documentBase.DocumentWithTableNavigation._tableMovementScriptHelper = originalTableScriptHelper
        cursorManager.CursorManager._set_selection = original_set_selection

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
        ui.message("BrowserNav navigates by " + BROWSE_MODES[mode])

    def generateBrowseModeExtractors(self):
        mode = getConfig("browserMode")
        if mode == 0:
            # horizontal offset
            extractFormattingFunc = lambda x: None
            extractIndentFunc = lambda textInfo,x: getSimpleHorizontalOffset(textInfo)
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
        ) = self.generateBrowseModeExtractors()

        focus = api.getFocusObject()
        focus = focus.treeInterceptor
        textInfo = focus.makeTextInfo(textInfos.POSITION_CARET)
        textInfo.expand(textInfos.UNIT_PARAGRAPH)
        origFormatting = extractFormattingFunc(textInfo)
        origIndent = extractIndentFunc(textInfo, origFormatting)
        origStyle = extractStyleFunc(textInfo, origFormatting)
        distance = 0
        while True:
            result =textInfo.move(textInfos.UNIT_PARAGRAPH, increment)
            if result == 0:
                return self.endOfDocument(errorMessage)
            textInfo.expand(textInfos.UNIT_PARAGRAPH)
            text = textInfo.text
            if speech.isBlank(text):
                continue
            formatting = extractFormattingFunc(textInfo)
            indent = extractIndentFunc(textInfo, formatting)
            style = extractStyleFunc(textInfo, formatting)
            if style == origStyle:
                if op(indent, origIndent):
                    self.beeper.simpleCrackle(distance, volume=getConfig("crackleVolume"))
                    speech.speakTextInfo(textInfo, reason=REASON_CARET)
                    textInfo.collapse()
                    textInfo.updateCaret()
                    selfself.selection = textInfo
                    return
            distance += 1


    def endOfDocument(self, message):
        volume = getConfig("noNextTextChimeVolume")
        self.beeper.fancyBeep("HF", 100, volume, volume)
        if getConfig("noNextTextMessage"):
            ui.message(message)

    def findMark(self, direction, regexp, errorMessage, selfself):
        r = re.compile(regexp)
        focus = api.getFocusObject().treeInterceptor
        textInfo = focus.makeTextInfo(textInfos.POSITION_CARET)
        textInfo.expand(textInfos.UNIT_PARAGRAPH)
        distance = 0
        while True:
            distance += 1
            textInfo.collapse()
            result = textInfo.move(textInfos.UNIT_PARAGRAPH, direction)
            if result == 0:
                self.endOfDocument(errorMessage)
                return
            textInfo.expand(textInfos.UNIT_PARAGRAPH)
            m = r.search(textInfo.text)
            if m:
                textInfo.collapse()
                textInfo.move(textInfos.UNIT_CHARACTER, m.start(0))
                end = textInfo.copy()
                end.move(textInfos.UNIT_CHARACTER, len(m.group(0)))
                textInfo.setEndPoint(end, "endToEnd")
                textInfo.updateCaret()
                self.beeper.simpleCrackle(distance, volume=getConfig("crackleVolume"))
                speech.speakTextInfo(textInfo, reason=REASON_CARET)
                textInfo.collapse()
                focus._set_selection(textInfo)
                selfself.selection = textInfo
                return

    def isRolePresent(self, textInfo, roles):
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
                self.endOfDocument(errorMessage)
                return
            textInfo.expand(textInfos.UNIT_PARAGRAPH)
            if not newMethod:
                obj = textInfo.NVDAObjectAtStart
                testResult =  obj is not None and obj.role in roles
            else:
                testResult = self.isRolePresent(textInfo, roles)
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
                    self.endOfDocument(_("No next format change!"))
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
                self.endOfDocument(errorMessage)
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
            ui.message("Jupyter cell update in progress!")
            self.beeper.fancyBeep("AF#", length=100, left=20, right=20)
            return
        fg=winUser.getForegroundWindow()
        if not config.conf["virtualBuffers"]["autoFocusFocusableElements"]:
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
        if obj.role != controlTypes.ROLE_EDITABLETEXT:
            ui.message(_("Not editable"))
            return
        uniqueID = obj.IA2UniqueID
        self.startInjectingKeystrokes()
        try:
            kbdControlHome.send()
            kbdBackquote.send()
            try:
                kbdControlA.send()
                text = self.getSelection()
                if False:
                    # This alternative method doesn't work for large cells: apparently the selection is just "-" if your cell is too large :(
                    timeout = time.time() + 3
                    while True:
                        if time.time() > timeout:
                            raise EditBoxUpdateError(_("Time out while waiting for selection to appear."))
                        api.processPendingEvents(processEventQueue=False)
                        textInfo = obj.makeTextInfo(textInfos.POSITION_SELECTION)
                        text = textInfo.text
                        if len(text) != 0:
                            break
                        time.sleep(10/1000)
            finally:
                kbdControlHome.send()
                kbdDelete.send()
        finally:
            self.endInjectingKeystrokes()
        if (len(text) == 0) or (text[0] != '`'):
            ui.message("Failed to copy text from semi-accessible edit-box")
            return
        text = text[1:]
        def getFocusObjectVerified():
                focus = api.getFocusObject()
                if focus.role != controlTypes.ROLE_EDITABLETEXT:
                    raise EditBoxUpdateError(_("Browser state has changed. Focused element is not an edit box. Role: %d.") % focus.role)
                if (uniqueID is not None) and (uniqueID != 0):
                    if uniqueID != focus.IA2UniqueID:
                        raise EditBoxUpdateError(_("Browser state has changed. Different element on the page is now focused."))
                return focus

        def updateText(result, text, keystroke):
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
                        controlTypes.ROLE_PANE,
                        controlTypes.ROLE_FRAME,
                        controlTypes.ROLE_DOCUMENT,
                    ]:
                        # All good, Firefox is burning cpu, keep sleeping!
                        yield 10
                        goodCounter = 0
                        continue
                    elif focus.role == controlTypes.ROLE_EDITABLETEXT:
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
                    self.copyToClip(text)
                  # Step 3.1: Send Control+A and wait for the selection to appear
                    kbdControlHome.send()
                    # Sending backquote character to ensure that the edit box is not empty
                    kbdBackquote.send()
                    kbdControlA.send()
                    while True:
                        yield 1
                        focus = getFocusObjectVerified()
                        if time.time() > timeout:
                            raise EditBoxUpdateError(_("Timed out during Control+A stage"))
                        textInfo = focus.makeTextInfo(textInfos.POSITION_SELECTION)
                        text = textInfo.text
                        if len(text) > 0:
                            break
                  # Step 3.2 Send Control+V and wait for the selection to disappear
                    kbdControlV.send()
                    kbdControlHome.send()
                    while True:
                        yield 1
                        focus = getFocusObjectVerified()
                        if time.time() > timeout:
                            raise EditBoxUpdateError(_("Timed out during Control+V stage"))
                        textInfo = focus.makeTextInfo(textInfos.POSITION_SELECTION)
                        text = textInfo.text
                        if len(text) == 0:
                            break
                finally:
                  # Step 3.3. Sleep for a bit more just to make sure things have propagated.
                  # Apparently if we don't sleep, then either the previous value with ` would be used sometimes,
                  # or it will paste the original contents of clipboard.
                    yield 200
                    self.endInjectingKeystrokes()
              # Step 4: send the original keystroke, e.g. Control+Enter
                if keystroke is not None:
                    keystroke.send()
              # Step 5 Send Control+Shift+Down, so that NVDA at least sees the first line of each edit box
                # This is disabled, since selecting lines causes weird behavior in some edit boxes
                #for i in range(5):
                #    kbdControlShiftDown.send()

            except EditBoxUpdateError as e:
                tones.player.stop()
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
            text,
            lambda result, text, keystroke: executeAsynchronously(updateText(result, text, keystroke))
        )

    def script_copyJupyterText(self, gesture, selfself):
        if len(self.lastJupyterText) > 0:
            self.copyToClip(self.lastJupyterText)
            ui.message(_("Last Jupyter text has been copied to clipboard."))
        else:
            ui.message(_("No last Jupyter text., or last Jupyter text is empty."))

    def startInjectingKeystrokes(self):
        self.restoreKeyboardState()
        self.clipboardBackup = api.getClipData()

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
                raise Exception("Time out while trying to copy data out of application.")

            try:
                data = api.getClipData()
                if data != controlCharacter:
                    return data
            except PermissionError:
                pass
            wx.Yield()
            time.sleep(10/1000)

    def popupEditTextDialog(self, text, onTextComplete):
        gui.mainFrame.prePopup()
        d = EditTextDialog(gui.mainFrame, text, onTextComplete)
        result = d.Show()
        gui.mainFrame.postPopup()

    def script_toggleOption(self, gesture, selfself, option, messages):
        setConfig(option, not getConfig(option))
        message = messages[int(getConfig(option))]
        ui.message(message)

    def script_goBack(self, gesture, selfself):
        try:
            key = weakref.ref(selfself)
            with selectionHistoryLock:
                sh = selectionHistory[key]
        except KeyError:
            self.endOfDocument(_("No cursor history available"))
            return
        try:
            info = sh.goBack(selfself.selection)
        except  IndexError:
            self.endOfDocument(_("Cannot go back any more"))
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
            doc="Moves to next sibling in browser")
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Alt+UpArrow",
            "moveToPreviousSibling",
            doc="Moves to previous sibling in browser")
        self.injectBrowseModeKeystroke(
            ["kb:NVDA+Alt+LeftArrow", "kb:NVDA+Alt+Home"],
            "moveToParent",
            doc="Moves to next parent in browser")
        self.injectBrowseModeKeystroke(
            ["kb:NVDA+Control+Alt+LeftArrow", "kb:NVDA+Alt+End"],
            "moveToNextParent",
            doc="Moves to next parent in browser")
        self.injectBrowseModeKeystroke(
            ["kb:NVDA+Alt+RightArrow", "kb:NVDA+Alt+PageDown"],
            "moveToChild",
            doc="Moves to next child in browser")
        self.injectBrowseModeKeystroke(
            ["kb:NVDA+Control+Alt+RightArrow", "kb:NVDA+Alt+PageUp"],
            "moveToPreviousChild",
            doc="Moves to previous child in browser")
      #Rotor
        self.injectBrowseModeKeystroke(
            "kb:NVDA+O",
            "rotor",
            doc="Adjusts BrowserNav rotor")

      # Marks
        self.injectBrowseModeKeystroke(
            "kb:j",
            "nextMark",
            script=lambda selfself, gesture: self.findMark(1, getConfig("marks"), "No next browser mark. To configure browser marks, go to BrowserNav settings.", selfself=selfself),
            doc="Jump to next browser mark.")
        self.injectBrowseModeKeystroke(
            "kb:Shift+j",
            "previousMark",
            script=lambda selfself, gesture: self.findMark(-1, getConfig("marks"), _("No previous browser mark. To configure browser marks, go to BrowserNav settings."), selfself=selfself),
            doc="Jump to previous browser mark.")
        if False:
            self.injectBrowseModeKeystroke(
                "",
                "nextParagraph",
                script=lambda selfself, gesture: self.script_moveByParagraph_forward(gesture),
                doc="Jump to next paragraph")
            self.injectBrowseModeKeystroke(
                "",
                "previousParagraph",
                script=lambda selfself, gesture: self.script_moveByParagraph_back(gesture),
                doc="Jump to previous paragraph")
      # Tabs
        # Example page with tabs:
        # https://wet-boew.github.io/v4.0-ci/demos/tabs/tabs-en.html
        self.injectBrowseModeKeystroke(
            "kb:Y",
            "nextTab",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles={controlTypes.ROLE_TAB, controlTypes.ROLE_TABCONTROL},
                errorMessage=_("No next tab"),
                newMethod=True,
            ),
            doc="Jump to next tab")
        self.injectBrowseModeKeystroke(
            "kb:Shift+Y",
            "previousTab",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=[controlTypes.ROLE_TAB],
                errorMessage=_("No previous tab"),
                newMethod=True,
            ),
            doc="Jump to previous tab")

      #Dialog
        dialogTypes = [controlTypes.ROLE_APPLICATION, controlTypes.ROLE_DIALOG]
        self.injectBrowseModeKeystroke(
            "kb:P",
            "nextDialog",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles=dialogTypes,
                errorMessage=_("No next dialog")),
            doc="Jump to next dialog")
        self.injectBrowseModeKeystroke(
            "kb:Shift+P",
            "previousDialog",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=dialogTypes,
                errorMessage=_("No previous dialog")),
            doc="Jump to previous dialog")
      # Menus
        menuTypes = [
            controlTypes.ROLE_MENU,
            controlTypes.ROLE_MENUBAR,
            controlTypes.ROLE_MENUITEM,
            controlTypes.ROLE_POPUPMENU,
            controlTypes.ROLE_CHECKMENUITEM,
            controlTypes.ROLE_RADIOMENUITEM,
            controlTypes.ROLE_TEAROFFMENU,
            controlTypes.ROLE_MENUBUTTON,
        ]
        self.injectBrowseModeKeystroke(
            "kb:Z",
            "nextMenu",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles=menuTypes,
                errorMessage=_("No next menu")),
            doc="Jump to next menu")
        self.injectBrowseModeKeystroke(
            "kb:Shift+Z",
            "previousMenu",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=menuTypes,
                errorMessage=_("No previous menu")),
            doc="Jump to previous menu")

      # Tree views, tool bars
        self.injectBrowseModeKeystroke(
            "kb:0",
            "nextTreeView",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles=[controlTypes.ROLE_TREEVIEW],
                errorMessage=_("No next tree view")),
            doc="Jump to next tree view")
        self.injectBrowseModeKeystroke(
            "kb:Shift+0",
            "previousTreeView",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=[controlTypes.ROLE_TREEVIEW],
                errorMessage=_("No previous tree view")),
            doc="Jump to previous tree view")
        self.injectBrowseModeKeystroke(
            "kb:9",
            "nextToolBar",
            script=lambda selfself, gesture: self.findByControlField(
                direction=1,
                role=controlTypes.ROLE_TOOLBAR,
                errorMessage=_("No next tool bar")),
            doc="Jump to next tool bar")
        self.injectBrowseModeKeystroke(
            "kb:Shift+9",
            "previousToolBar",
            script=lambda selfself, gesture: self.findByControlField(
                direction=-1,
                role=controlTypes.ROLE_TOOLBAR,
                errorMessage=_("No previous tool bar")),
            doc="Jump to previous tool bar")
      #Format change
        self.injectBrowseModeKeystroke(
            "kb:`",
            "nextFormatChange",
            script=lambda selfself, gesture: self.findFormatChange(
                selfself,
                direction=1,
                errorMessage=_("No next format change")),
            doc="Jump to next format change")
        self.injectBrowseModeKeystroke(
            "kb:Shift+`",
            "previousFormatChange",
            script=lambda selfself, gesture: self.findFormatChange(
                selfself,
                direction=-1,
                errorMessage=_("No previous format change")),
            doc="Jump to previous format change")
      # Scroll all:
        self.injectBrowseModeKeystroke(
            "kb:\\",
            "scrollAllForward",
            script=lambda selfself, gesture: self.scrollToAll(
                direction=1,
                message=_("Scrolling forward. This may load more elements on the page.")),
            doc="Scroll to all possible elements forward")
        self.injectBrowseModeKeystroke(
            "kb:Shift+\\",
            "scrollAllBackward",
            script=lambda selfself, gesture: self.scrollToAll(
                direction=-1,
                message=_("Scrolling backward. This may load more elements on the page.")),
            doc="Scroll to all possible elements backward")

      # Edit Jupyter
        self.injectBrowseModeKeystroke(
            "kb:NVDA+E",
            "editJupyter",
            script=lambda selfself, gesture: self.script_editJupyter(gesture, selfself),
            doc="Edit semi-accessible edit box.")
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Control+E",
            "copyJupyterText",
            script=lambda selfself, gesture: self.script_copyJupyterText(gesture, selfself),
            doc="Copy the last text from semi-accessible edit box to clipboard.")
      # Toggle skip mode
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Control+/",
            "toggleSkipEmptyParagraphs",
            script=lambda selfself, gesture: self.script_toggleOption(
                gesture,
                selfself,
                "skipEmptyParagraphs",
                [
                    _("Not skipping over empty paragraphs and paragraphs matching skip regex "),
                    _("Skipping over empty paragraphs and paragraphs matching skip regex "),
                ]
            ),
            doc="Toggle skipping over empty paragraphs and paragraphs matching skip regex")
        self.injectBrowseModeKeystroke(
            "kb:NVDA+/",
            "toggleSkipEmptyLines",
            script=lambda selfself, gesture: self.script_toggleOption(
                gesture,
                selfself,
                "skipEmptyLines",
                [
                    _("Not skipping over empty lines and lines matching skip regex "),
                    _("Skipping over empty lines and lines matching skip regex "),
                ]
            ),
            doc="Toggle skipping over empty lines and lines matching skip regex")
      # Go back in browse mode
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Shift+LeftArrow",
            "goBack",
            script=lambda selfself, gesture: self.script_goBack(
                gesture,
                selfself,
            ),
            doc="Experimental: go back to the previous location of cursor in current document")