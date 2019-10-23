#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2019 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

# This addon allows to navigate documents by indentation or offset level.
# In browsers you can navigate by object location on the screen.
# In editable text fields you can navigate by the indentation level.
# This is useful for editing source code.
# Author: Tony Malykh <anton.malykh@gmail.com>
# https://github.com/mltony/nvda-indent-nav/
# Original author: Sean Mealin <spmealin@gmail.com>

import addonHandler
import api
import browseMode
import controlTypes
import config
import ctypes
import globalPluginHandler
import gui
import NVDAHelper
import operator
import re
import scriptHandler
from scriptHandler import script
import speech
import struct
import textInfos
import tones
import ui
import wx

def myAssert(condition):
    if not condition:
        raise RuntimeError("Assertion failed")


def initConfiguration():
    confspec = {
        "crackleVolume" : "integer( default=25, min=0, max=100)",
        "noNextTextChimeVolume" : "integer( default=50, min=0, max=100)",
        "noNextTextMessage" : "boolean( default=True)",
        "browserMode" : "integer( default=0, min=0, max=2)",
        "useFontFamily" : "boolean( default=True)",
        "useColor" : "boolean( default=True)",
        "useBackgroundColor" : "boolean( default=True)",
        "useBoldItalic" : "boolean( default=True)",
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

    def onOk(self, evt):
        config.conf["browsernav"]["crackleVolume"] = self.crackleVolumeSlider.Value
        config.conf["browsernav"]["noNextTextChimeVolume"] = self.noNextTextChimeVolumeSlider.Value
        config.conf["browsernav"]["noNextTextMessage"] = self.noNextTextMessageCheckbox.Value
        config.conf["browsernav"]["useFontFamily"] = self.useFontFamilyCheckBox.Value
        config.conf["browsernav"]["useColor"] = self.useColorCheckBox.Value
        config.conf["browsernav"]["useBackgroundColor"] = self.useBackgroundColorCheckBox.Value
        config.conf["browsernav"]["useBoldItalic"] = self.useBoldItalicCheckBox.Value
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

class Beeper:
    BASE_FREQ = speech.IDT_BASE_FREQUENCY
    def getPitch(self, indent):
        return self.BASE_FREQ*2**(indent/24.0) #24 quarter tones per octave.

    BEEP_LEN = 10 # millis
    PAUSE_LEN = 5 # millis
    MAX_CRACKLE_LEN = 400 # millis
    MAX_BEEP_COUNT = MAX_CRACKLE_LEN // (BEEP_LEN + PAUSE_LEN)


    def fancyCrackle(self, levels, volume):
        levels = self.uniformSample(levels, self.MAX_BEEP_COUNT )
        beepLen = self.BEEP_LEN
        pauseLen = self.PAUSE_LEN
        pauseBufSize = NVDAHelper.generateBeep(None,self.BASE_FREQ,pauseLen,0, 0)
        beepBufSizes = [NVDAHelper.generateBeep(None,self.getPitch(l), beepLen, volume, volume) for l in levels]
        bufSize = sum(beepBufSizes) + len(levels) * pauseBufSize
        buf = ctypes.create_string_buffer(bufSize)
        bufPtr = 0
        for l in levels:
            bufPtr += NVDAHelper.generateBeep(
                ctypes.cast(ctypes.byref(buf, bufPtr), ctypes.POINTER(ctypes.c_char)),
                self.getPitch(l), beepLen, volume, volume)
            bufPtr += pauseBufSize # add a short pause
        tones.player.stop()
        tones.player.feed(buf.raw)

    def simpleCrackle(self, n, volume):
        return self.fancyCrackle([0] * n, volume)


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
        tones.player.stop()
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
        tones.player.feed(packed)

    def uniformSample(self, a, m):
        n = len(a)
        if n <= m:
            return a
        # Here assume n > m
        result = []
        for i in range(0, m*n, n):
            result.append(a[i  // m])
        return result




class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("BrowserNav")
    beeper = Beeper()

    def __init__(self, *args, **kwargs):
        super(GlobalPlugin, self).__init__(*args, **kwargs)
        self.createMenu()
        self.injectBrowseModeKeystrokes()

    def createMenu(self):
        def _popupMenu(evt):
            gui.mainFrame._popupSettingsDialog(SettingsDialog)
        self.prefsMenuItem  = gui.mainFrame.sysTrayIcon.preferencesMenu.Append(wx.ID_ANY, _("BrowserNav..."))
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, _popupMenu, self.prefsMenuItem)

    def terminate(self):
        prefMenu = gui.mainFrame.sysTrayIcon.preferencesMenu
        prefMenu.Remove(self.prefsMenuItem)

    def script_moveToNextSibling(self, gesture):
        mode = getMode()
        # Translators: error message if next sibling couldn't be found
        errorMessage = _("No next paragraph with the same {mode} in the document").format(
            mode=BROWSE_MODES[mode])
        self.moveInBrowser(1, errorMessage, operator.eq)

    def script_moveToPreviousSibling(self, gesture):
        mode = getMode()
        # Translators: error message if previous sibling couldn't be found
        errorMessage = _("No previous paragraph with the same {mode} in the document").format(
            mode=BROWSE_MODES[mode])
        self.moveInBrowser(-1, errorMessage, operator.eq)


    def script_moveToParent(self, gesture):
        mode = getMode()
        op = PARENT_OPERATORS[mode]
        # Translators: error message if parent could not be found
        errorMessage = _("No paragraph  with {qualifier} {mode} in the document").format(
            mode=BROWSE_MODES[mode],
            qualifier=OPERATOR_STRINGS[op])
        self.moveInBrowser(-1, errorMessage, op)

    def script_moveToChild(self, gesture):
        mode = getMode()
        op = CHILD_OPERATORS[mode]
        # Translators: error message if parent could not be found
        errorMessage = _("No paragraph  with {qualifier} {mode} in the document").format(
            mode=BROWSE_MODES[mode],
            qualifier=OPERATOR_STRINGS[op])
        self.moveInBrowser(1, errorMessage, op)

    def script_rotor(self, gesture):
        mode = getMode()
        mode = (mode + 1) % len(BROWSE_MODES)
        setConfig("browserMode", mode)
        ui.message("BrowserNav navigates by " + BROWSE_MODES[mode])

    def generateBrowseModeExtractors(self):
        def getFontSize(textInfo, formatting):
            try:
                size =float( formatting["font-size"].replace("pt", ""))
                return size
            except:
                return 0
        mode = getConfig("browserMode")
        if mode == 0:
            # horizontal offset
            extractFormattingFunc = lambda x: None
            extractIndentFunc = lambda textInfo,x: textInfo.NVDAObjectAtStart.location[0]
            extractStyleFunc = lambda x,y: None
        elif mode in [1,2]:
            extractFormattingFunc = lambda textInfo: self.getFormatting(textInfo)
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
    def getFormatting(self, info):
        formatField=textInfos.FormatField()
        formatConfig=config.conf['documentFormatting']
        for field in info.getTextWithFields(formatConfig):
            #if isinstance(field,textInfos.FieldCommand): and isinstance(field.field,textInfos.FormatField):
            try:
                formatField.update(field.field)
            except:
                pass
        return formatField

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

    def moveInBrowser(self, increment, errorMessage, op):
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
                    textInfo.updateCaret()
                    self.beeper.simpleCrackle(distance, volume=getConfig("crackleVolume"))
                    speech.speakTextInfo(textInfo, reason=controlTypes.REASON_CARET)
                    return
            distance += 1


    def endOfDocument(self, message):
        volume = getConfig("noNextTextChimeVolume")
        self.beeper.fancyBeep("HF", 100, volume, volume)
        if getConfig("noNextTextMessage"):
            ui.message(message)

    def findByRole(self, direction, roles, errorMessage):
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
            obj = textInfo.NVDAObjectAtStart
            if obj is not None and obj.role in roles:
                textInfo.updateCaret()
                self.beeper.simpleCrackle(distance, volume=getConfig("crackleVolume"))
                speech.speakTextInfo(textInfo, reason=controlTypes.REASON_CARET)
                return


    def injectBrowseModeKeystroke(self, keystroke, funcName, script=None, doc=None):
        gp = self
        cls = browseMode.BrowseModeTreeInterceptor
        scriptFuncName = "script_" + funcName
        if script is None:
            gpFunc = getattr(gp, scriptFuncName)
            script = lambda self, gesture: gpFunc(gesture)
        script.__name__ = scriptFuncName
        script.category = "BrowserNav"
        if doc is not None:
            script.__doc__ = doc
        setattr(cls, scriptFuncName, script)
        cls._BrowseModeTreeInterceptor__gestures[keystroke] = funcName

    def injectBrowseModeKeystrokes(self):
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Alt+DownArrow",
            "moveToNextSibling",
            doc="Moves to next sibling in browser")
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Alt+UpArrow",
            "moveToPreviousSibling",
            doc="Moves to previous sibling in browser")
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Alt+LeftArrow",
            "moveToParent",
            doc="Moves to parent in browser")
        self.injectBrowseModeKeystroke(
            "kb:NVDA+Alt+RightArrow",
            "moveToChild",
            doc="Moves to next child in browser")
        self.injectBrowseModeKeystroke(
            "kb:NVDA+O",
            "rotor",
            doc="Adjusts BrowserNav rotor")
        self.injectBrowseModeKeystroke(
            "kb:P",
            "nextParagraph",
            script=lambda selfself, gesture: self.script_moveByParagraph_forward(gesture),
            doc="Jump to next paragraph")
        self.injectBrowseModeKeystroke(
            "kb:Shift+P",
            "previousParagraph",
            script=lambda selfself, gesture: self.script_moveByParagraph_back(gesture),
            doc="Jump to previous paragraph")
        # Example page with tabs:
        # https://wet-boew.github.io/v4.0-ci/demos/tabs/tabs-en.html
        self.injectBrowseModeKeystroke(
            "kb:Y",
            "nextTab",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles=[controlTypes.ROLE_TAB],
                errorMessage=_("No next tab")),
            doc="Jump to next tab")
        self.injectBrowseModeKeystroke(
            "kb:Shift+Y",
            "previousTab",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=[controlTypes.ROLE_TAB],
                errorMessage=_("No previous tab")),
            doc="Jump to previous tab")

        #Dialog
        dialogTypes = [controlTypes.ROLE_APPLICATION, controlTypes.ROLE_DIALOG]
        self.injectBrowseModeKeystroke(
            "kb:J",
            "nextDialog",
            script=lambda selfself, gesture: self.findByRole(
                direction=1,
                roles=dialogTypes,
                errorMessage=_("No next dialog")),
            doc="Jump to next dialog")
        self.injectBrowseModeKeystroke(
            "kb:Shift+J",
            "previousDialog",
            script=lambda selfself, gesture: self.findByRole(
                direction=-1,
                roles=dialogTypes,
                errorMessage=_("No previous dialog")),
            doc="Jump to previous dialog")

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
