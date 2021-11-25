#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import api
from controlTypes import OutputReason
import copy
import dataclasses
from dataclasses import dataclass
#from dataclasses_json import dataclass_json
from enum import Enum
import functools
import globalVars
import gui
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import SettingsPanel
import json
import os
import re
import tones
from typing import List
import wx

debug = True
if debug:
    f = open("C:\\Users\\tony\\drp\\2.txt", "w")
    def mylog(s):
        if debug:
            print(str(s), file=f)
            f.flush()
else:
    def mylog(s):
        pass
class RuleCategory(Enum):
    QUICK_JUMP = 1
    QUICK_JUMP_2 = 2
    QUICK_JUMP_3 = 3
    SKIP_CLUTTER = 4
    AUTO_PRESS = 5

ruleCategoryNames = {
    RuleCategory.QUICK_JUMP: _('QuickJump - assigned to J by default'),
    RuleCategory.QUICK_JUMP_2: _('QuickJump2'),
    RuleCategory.QUICK_JUMP_3: _('QuickJump3'),
    RuleCategory.SKIP_CLUTTER: _('SkipClutter - will automatically skip this paragraph or line when navigating via Control+Up/Down or Up/Down keystrokes; must match the whole paragraph. or '),
    RuleCategory.AUTO_PRESS: _('AutoPress'),
}

class URLMatch(Enum):
    IGNORE = 0
    DOMAIN = 1
    SUBDOMAIN = 2
    SUBSTRING = 3
    EXACT = 4
    REGEX = 5

urlMatchNames = {
    URLMatch.IGNORE: _('Match all sites (domain field ignored) '),
    URLMatch.DOMAIN: _('Match domain name'),
    URLMatch.SUBDOMAIN: _('Match domain and its subdomains'),
    URLMatch.SUBSTRING: _('Match substring in URL'),
    URLMatch.EXACT: _('Exact URL match'),
    URLMatch.REGEX: _('Regex match of URL'),
}

class FocusMode(Enum):
    UNCHANGED = 0
    DONT_ENTER_FORM_MODE = 1
    DISABLE_FOCUS = 2

focusModeNames = {
    FocusMode.UNCHANGED: _('Keep default NVDA focus behavior'),
    FocusMode.DONT_ENTER_FORM_MODE: _('React to focus event, but prevent entering focus mode'),
    FocusMode.DISABLE_FOCUS: _('Ignore all focus events - good for websites that misuse focus events'),
}



class PatternMatch(Enum):
    EXACT = 1
    SUBSTRING = 2
    REGEX = 3

patterMatchNames = {
    PatternMatch.EXACT: _('Exact paragraph match'),
    PatternMatch.SUBSTRING: _('Substring paragraph match'),
    PatternMatch.REGEX: _('Regex paragraph match'),
}

@dataclass
class QJRule:
    enabled: bool
    category: RuleCategory
    name: str
    pattern: str
    patternMatch: PatternMatch

    def __init__(self, d):
        self.enabled = d['enabled']
        self.category = RuleCategory(URLMatch(d['category']))
        self.name = d['name']
        self.pattern = d['pattern']
        self.patternMatch = PatternMatch(d['patternMatch'])

    def asDict(self):
        return {
            'enabled': self.enabled,
            'category': self.category.value,
            'name': self.name,
            'pattern': self.pattern,
            'patternMatch': self.patternMatch.value,
        }

    def getDisplayName(self):
        if self.name is not None and len(self.name) > 0:
            return self.name
        return self.pattern

    def __hash__(self):
        return id(self)



@dataclass
class QJSite:
    domain: str
    urlMatch: URLMatch
    name: str
    focusMode: FocusMode
    rules: List[QJRule]

    def __init__(self, d):
        self.domain = d['domain']
        self.urlMatch = URLMatch(d['urlMatch'])
        self.name = d['name']
        self.focusMode = FocusMode(d.get('focusMode', FocusMode.UNCHANGED))
        self.rules = [
            QJRule(ruleDict)
            for ruleDict in d.get('rules', [])
        ]

    def asDict(self):
        return {
            'domain': self.domain,
            'urlMatch': self.urlMatch.value,
            'name': self.name,
            'focusMode': self.focusMode.value,
            'rules': [rule.asDict() for rule in self.rules]
        }


    def postLoad(self):
        self.urlMatch = URLMatch(self.urlMatch)
        return self

    def getDisplayName(self):
        if self.name is not None and len(self.name) > 0:
            return self.name
        return self.domain

    def __hash__(self):
        return id(self)




@dataclass
class QJConfig:
    # WARNING!
    # Please treat instances of this class as immutable
    # This class is hashable on id, so any change of global config object will lead to nasty and hard-to-debug side effects.

    sites: List[QJSite]
    rules: List[QJRule]

    def __init__(self, d):
        self.sites = [
            QJSite(item)
            for item in d['sites']
        ]
        self.rules = [
            QJRule(**item).postLoad()
            for item in d['rules']
        ]

    def asDict(self):
        return {
            'sites': [
                site.asDict()
                for site in self.sites
            ],
            'rules': [
                dataclasses.asdict(rule)
                for rule in self.rules
            ],
        }

    def __hash__(self):
        return id(self)

rulesFileName = os.path.join(globalVars.appArgs.configPath, "browserNavRules.json")
defaultRulesFileName = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "browserNavRules.json"
)

def loadConfig():
    try:
        rulesConfig = open(rulesFileName, "r").read()
        mylog(rulesFileName)
    except FileNotFoundError:
        rulesConfig = open(defaultRulesFileName, "r").read()
        mylog(defaultRulesFileName)
    return QJConfig(json.loads(rulesConfig))


def saveConfig():
    global config
    configDict = config.asDict()
    rulesJson = json.dumps(configDict, indent=4, sort_keys=True)
    rulesFile = open(rulesFileName, "w")
    try:
        rulesFile.write(rulesJson)
    finally:
        rulesFile.close()

config  = loadConfig()
api.q=config

if False:
    from dataclasses import dataclass, asdict
    from enum import Enum


    @dataclass
    class Foobar:
      name: str
      template: "FoobarEnum"


    class FoobarEnum(Enum):
      FIRST = "foobar"
      SECOND = "baz"


    def custom_asdict_factory(data):

        def convert_value(obj):
            if isinstance(obj, Enum):
                return obj.value
            return obj

        return dict((k, convert_value(v)) for k, v in data)


    foobar = Foobar(name="John", template=FoobarEnum.FIRST)

    print(asdict(foobar, dict_factory=custom_asdict_factory))
    # {'name': 'John', 'template': 'foobar'}

@functools.lru_cache()
def re_compile(s):
    return re.compile(s)

@functools.lru_cache()
def isUrlMatch(url, site):
    if site.urlMatch == URLMatch.IGNORE:
        return True
    elif site.urlMatch in {URLMatch.DOMAIN, URLMatch.SUBDOMAIN}:
        m = re_compile(
            # http://
                r'(\w+://)?'
            # username:password@
                + r'([\w.,:"-]+@)?'
            # google.com
                + r'(?P<domain>[\w.-]+)'
            # :80
                +r'(:\d+)?'
            # /rest/of/the/url#...
                +r'.*'
        ).match(url)
        if not m:
            return False
        domain = m.group('domain').lower()
        siteDomain = site.domain.lower()
        if site.urlMatch == URLMatch.DOMAIN:
            return domain == site_domain
        elif site.urlMatch == URLMatch.SUBDOMAIN:
            return (
                domain == siteDomain
                or domain.endswith("." + siteDomain)
            )
        else:
            raise Exception("Impossible!")
    elif site.urlMatch == URLMatch.SUBSTRING:
        return site.domain.lower() in url.lower()
    elif site.urlMatch == URLMatch.EXACT:
        return site.domain.lower() ==  url.lower()
    elif site.urlMatch == URLMatch.REGEX:
        return re_compile(site.domain).match(url) is not None

@functools.lru_cache()
def findSites(url, config):
    return [
        site
        for site in config.sites
        if isUrlMatch(url, site)
    ]

@functools.lru_cache()
def getFocusMode(url, config):
    sites = findSites(url, config)
    if len(sites) == 0:
        return FocusMode.UNCHANGED
    mode = max([
        site.focusMode.value
        for site in sites
    ])
    return FocusMode(mode)

originalShouldPassThrough = None
def newShouldPassThrough(self, obj, reason= None):
    focusMode = getFocusMode(self.documentConstantIdentifier, config)
    if reason == OutputReason.FOCUS and focusMode == FocusMode.DONT_ENTER_FORM_MODE:
        return self.passThrough
    else:
        return originalShouldPassThrough(self, obj, reason)

original_event_gainFocus = None
def new_event_gainFocus(self, obj, nextHandler):
    focusMode = getFocusMode(self.documentConstantIdentifier, config)
    if focusMode == FocusMode.DISABLE_FOCUS:
        return nextHandler()
    return original_event_gainFocus(self, obj, nextHandler)

class RuleDialog(wx.Dialog):
    def __init__(self, parent, title=_("Edit audio rule")):
        super(RuleDialog,self).__init__(parent,title=title)
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

      # Translators: label for pattern  edit field in add Audio Rule dialog.
        patternLabelText = _("&Pattern")
        self.patternTextCtrl=sHelper.addLabeledControl(patternLabelText, wx.TextCtrl)

      # Translators: label for case sensitivity  checkbox in add audio rule dialog.
        #caseSensitiveText = _("Case &sensitive")
        #self.caseSensitiveCheckBox=sHelper.addItem(wx.CheckBox(self,label=caseSensitiveText))

      # Translators: label for rule_enabled  checkbox in add audio rule dialog.
        enabledText = _("Rule enabled")
        self.enabledCheckBox=sHelper.addItem(wx.CheckBox(self,label=enabledText))
        self.enabledCheckBox.SetValue(True)
      # Translators:  label for type selector radio buttons in add audio rule dialog
        typeText = _("&Type")
        typeChoices = [AudioRuleDialog.TYPE_LABELS[i] for i in AudioRuleDialog.TYPE_LABELS_ORDERING]
        self.typeRadioBox=sHelper.addItem(wx.RadioBox(self,label=typeText, choices=typeChoices))
        self.typeRadioBox.Bind(wx.EVT_RADIOBOX,self.onType)
        self.setType(audioRuleBuiltInWave)

        self.typeControls = {
            audioRuleBuiltInWave: [],
            audioRuleWave: [],
            audioRuleBeep: [],
            audioRuleProsody: [],
        }

      # Translators: built in wav category  combo box
        biwCategoryLabelText=_("&Category:")
        self.biwCategory=guiHelper.LabeledControlHelper(
            self,
            biwCategoryLabelText,
            wx.Choice,
            choices=self.getBiwCategories(),
        )
        self.biwCategory.control.Bind(wx.EVT_CHOICE,self.onBiwCategory)
        self.typeControls[audioRuleBuiltInWave].append(self.biwCategory.control)
      # Translators: built in wav file combo box
        biwListLabelText=_("&Wave:")
        #self.biwList = sHelper.addLabeledControl(biwListLabelText, wx.Choice, choices=self.getBuiltInWaveFiles())
        self.biwList=guiHelper.LabeledControlHelper(
            self,
            biwListLabelText,
            wx.Choice,
            choices=[],
        )

        self.biwList.control.Bind(wx.EVT_CHOICE,self.onBiw)
        self.typeControls[audioRuleBuiltInWave].append(self.biwList.control)
      # Translators: wav file edit box
        self.wavName  = sHelper.addLabeledControl(_("Wav file"), wx.TextCtrl)
        #self.wavName.Disable()
        self.typeControls[audioRuleWave].append(self.wavName)

      # Translators: This is the button to browse for wav file
        self._browseButton = sHelper.addItem (wx.Button (self, label = _("&Browse...")))
        self._browseButton.Bind(wx.EVT_BUTTON, self._onBrowseClick)
        self.typeControls[audioRuleWave].append(self._browseButton)
      # Translators: label for adjust start
        label = _("Start adjustment in millis - positive to cut off start, negative for extra pause in the beginning.")
        self.startAdjustmentTextCtrl=sHelper.addLabeledControl(label, wx.TextCtrl)
        self.typeControls[audioRuleWave].append(self.startAdjustmentTextCtrl)
        self.typeControls[audioRuleBuiltInWave].append(self.startAdjustmentTextCtrl)
      # Translators: label for adjust end
        label = _("End adjustment in millis - positive for early cut off, negative for extra pause in the end")
        self.endAdjustmentTextCtrl=sHelper.addLabeledControl(label, wx.TextCtrl)
        self.typeControls[audioRuleWave].append(self.endAdjustmentTextCtrl)
        self.typeControls[audioRuleBuiltInWave].append(self.endAdjustmentTextCtrl)
      # Translators: label for tone
        toneLabelText = _("&Tone")
        self.toneTextCtrl=sHelper.addLabeledControl(toneLabelText, wx.TextCtrl)
        #self.toneTextCtrl.Disable()
        self.typeControls[audioRuleBeep].append(self.toneTextCtrl)
      # Translators: label for duration
        durationLabelText = _("Duration in milliseconds:")
        self.durationTextCtrl=sHelper.addLabeledControl(durationLabelText, wx.TextCtrl)
        #self.durationTextCtrl.Disable()
        self.typeControls[audioRuleBeep].append(self.durationTextCtrl)
      # Translators: prosody name comboBox
        prosodyNameLabelText=_("&Prosody name:")
        self.prosodyNameCategory=guiHelper.LabeledControlHelper(
            self,
            prosodyNameLabelText,
            wx.Choice,
            choices=self.PROSODY_LABELS,
        )
        self.typeControls[audioRuleProsody].append(self.prosodyNameCategory.control)
      # Translators: label for prosody offset
        prosodyOffsetLabelText = _("Prosody offset:")
        self.prosodyOffsetTextCtrl=sHelper.addLabeledControl(prosodyOffsetLabelText, wx.TextCtrl)
        self.typeControls[audioRuleProsody].append(self.prosodyOffsetTextCtrl)
      # Translators: label for prosody multiplier
        prosodyMultiplierLabelText = _("Prosody multiplier:")
        self.prosodyMultiplierTextCtrl=sHelper.addLabeledControl(prosodyMultiplierLabelText, wx.TextCtrl)
        self.typeControls[audioRuleProsody].append(self.prosodyMultiplierTextCtrl)

      # Translators: label for comment edit box
        commentLabelText = _("&Comment")
        self.commentTextCtrl=sHelper.addLabeledControl(commentLabelText, wx.TextCtrl)
      # Translators: This is the button to test audio rule
        self.testButton = sHelper.addItem (wx.Button (self, label = _("&Test, press twice for repeated sound")))
        self.testButton.Bind(wx.EVT_BUTTON, self.onTestClick)

        sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))

        mainSizer.Add(sHelper.sizer,border=20,flag=wx.ALL)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        self.patternTextCtrl.SetFocus()
        self.Bind(wx.EVT_BUTTON,self.onOk,id=wx.ID_OK)
        self.onType(None)

    def getType(self):
        typeRadioValue = self.typeRadioBox.GetSelection()
        if typeRadioValue == wx.NOT_FOUND:
            return audioRuleBuiltInWave
        return AudioRuleDialog.TYPE_LABELS_ORDERING[typeRadioValue]

    def setType(self, type):
        self.typeRadioBox.SetSelection(AudioRuleDialog.TYPE_LABELS_ORDERING.index(type))

    def getInt(self, s):
        if len(s) == 0:
            return None
        return int(s)

    def editRule(self, rule):
        self.commentTextCtrl.SetValue(rule.comment)
        self.patternTextCtrl.SetValue(rule.pattern)
        self.setType(rule.ruleType)
        self.wavName.SetValue(rule.wavFile)
        self.setBiw(rule.builtInWavFile)
        self.startAdjustmentTextCtrl.SetValue(str(rule.startAdjustment or 0))
        self.endAdjustmentTextCtrl.SetValue(str(rule.endAdjustment or 0))
        self.toneTextCtrl.SetValue(str(rule.tone or 500))
        self.durationTextCtrl.SetValue(str(rule.duration or 50))
        self.enabledCheckBox.SetValue(rule.enabled)
        try:
            prosodyCategoryIndex = self.PROSODY_LABELS.index(rule.prosodyName)
        except ValueError:
            prosodyCategoryIndex = 0
        self.prosodyNameCategory.control.SetSelection(prosodyCategoryIndex)
        self.prosodyOffsetTextCtrl.SetValue(str(rule.prosodyOffset or ""))
        self.prosodyMultiplierTextCtrl.SetValue(str(rule.prosodyMultiplier or ""))
        #self.caseSensitiveCheckBox.SetValue(rule.caseSensitive)
        self.onType(None)

    def makeRule(self):
        if not self.patternTextCtrl.GetValue():
            # Translators: This is an error message to let the user know that the pattern field is not valid.
            gui.messageBox(_("A pattern is required."), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
            self.patternTextCtrl.SetFocus()
            return
        try:
            re.compile(self.patternTextCtrl.GetValue())
        except sre_constants.error:
            # Translators: Invalid regular expression
            gui.messageBox(_("Invalid regular expression."), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
            self.patternTextCtrl.SetFocus()
            return

        if self.getType() == audioRuleWave:
            if not self.wavName.GetValue() or not os.path.exists(self.wavName.GetValue()):
                # Translators: wav file not found
                gui.messageBox(_("Wav file not found."), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
                self.wavName.SetFocus()
                return
            try:
                wave.open(self.wavName.GetValue(), "r").close()
            except wave.Error:
                # Translators: Invalid wav file
                gui.messageBox(_("Invalid wav file."), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
                self.wavName.SetFocus()
                return
        try:
            self.getInt(self.startAdjustmentTextCtrl.GetValue())
        except ValueError:
            # Translators: Invalid regular expression
            gui.messageBox(_("Start adjustment must be a number."), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
            self.startAdjustmentTextCtrl.SetFocus()
            return
        try:
            self.getInt(self.endAdjustmentTextCtrl.GetValue())
        except ValueError:
            # Translators: Invalid regular expression
            gui.messageBox(_("End adjustment must be a number."), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
            self.endAdjustmentTextCtrl.SetFocus()
            return
        if self.getType() == audioRuleBeep:
            good = False
            try:
                tone = self.getInt(self.toneTextCtrl.GetValue())
                if 0 <= tone <= 50000:
                    good = True
            except ValueError:
                pass
            if not good:
                gui.messageBox(_("tone must be an integer between 0 and 50000"), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
                self.toneTextCtrl.SetFocus()
                return

            good = False
            try:
                duration = self.getInt(self.durationTextCtrl.GetValue())
                if 0 <= duration <= 60000:
                    good = True
            except ValueError:
                pass
            if not good:
                gui.messageBox(_("duration must be an integer between 0 and 60000"), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
                self.durationTextCtrl.SetFocus()
                return
        prosodyOffset = None
        prosodyMultiplier = None
        if self.getType() == audioRuleProsody:
            good = False
            try:
                if len(self.prosodyOffsetTextCtrl.GetValue()) == 0:
                    prosodyOffset = None
                    good = True
                else:
                    prosodyOffset = self.getInt(self.prosodyOffsetTextCtrl.GetValue())
                    if -100 <= prosodyOffset <= 100:
                        good = True
            except ValueError:
                pass
            if not good:
                gui.messageBox(_("prosody offset must be an integer between -100 and 100"), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
                self.prosodyOffsetTextCtrl.SetFocus()
                return
            good = False
            try:
                if len(self.prosodyMultiplierTextCtrl.GetValue()) == 0:
                    prosodyMultiplier = None
                    good = True
                else:
                    prosodyMultiplier = float(self.prosodyOffsetTextCtrl.GetValue())
                    if .1 <= prosodyMultiplier <= 10:
                        good = True
            except ValueError:
                pass
            if not good:
                gui.messageBox(_("prosody multiplier must be a float between 0.1 and 10"), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
                self.prosodyMultiplierTextCtrl.SetFocus()
                return
            if prosodyOffset is not None and prosodyMultiplier is not None:
                gui.messageBox(_("You must specify either prosody offset or multiplier but not both"), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
                self.prosodyOffsetTextCtrl.SetFocus()
                return
            if prosodyOffset is  None and prosodyMultiplier is  None:
                gui.messageBox(_("You must specify either prosody offset or multiplier."), _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
                self.prosodyOffsetTextCtrl.SetFocus()
                return
            mylog(f"prosodyOffset={prosodyOffset}")
            mylog(f"prosodyMultiplier={prosodyMultiplier}")

        try:
            return AudioRule(
                comment=self.commentTextCtrl.GetValue(),
                pattern=self.patternTextCtrl.GetValue(),
                ruleType=self.getType(),
                wavFile=self.wavName.GetValue(),
                builtInWavFile=self.getBiw(),
                startAdjustment=self.getInt(self.startAdjustmentTextCtrl.GetValue()) or 0,
                endAdjustment=self.getInt(self.endAdjustmentTextCtrl.GetValue()) or 0,
                tone=self.getInt(self.toneTextCtrl.GetValue()),
                duration=self.getInt(self.durationTextCtrl.GetValue()),
                enabled=bool(self.enabledCheckBox.GetValue()),
                prosodyName=self.PROSODY_LABELS[self.prosodyNameCategory.control.GetSelection()],
                prosodyOffset=prosodyOffset,
                prosodyMultiplier=prosodyMultiplier,
                #caseSensitive=bool(self.caseSensitiveCheckBox.GetValue()),
            )
        except Exception as e:
            log.error("Could not add Audio Rule", e)
            # Translators: This is an error message to let the user know that the Audio rule is not valid.
            gui.messageBox(
                _(f"Error creating audio rule: {e}"),
                _("Audio rule Error"),
                wx.OK|wx.ICON_WARNING, self
            )
            return


    def onOk(self,evt):
        rule = self.makeRule()
        if rule is not None:
            self.rule = rule
            evt.Skip()

    def _onBrowseClick(self, evt):
        p= 'c:'
        while True:
            # Translators: browse wav file message
            fd = wx.FileDialog(self, message=_("Select wav file:"),
                wildcard="*.wav",
                defaultDir=os.path.dirname(p), style=wx.FD_OPEN
            )
            if not fd.ShowModal() == wx.ID_OK: break
            p = fd.GetPath()
            self.wavName.SetValue(p)
            break

    def onTestClick(self, evt):
        global rulesDialogOpen
        if time.time() - self.lastTestTime < 1:
            # Button pressed twice within a second
            repeat = True
        else:
            repeat = False
        self.lastTestTime = time.time()
        rulesDialogOpen = False
        try:
            rule = self.makeRule()
            if rule is None:
                return
            preText = _("Hello")
            postText = _("world")
            if not repeat:
                utterance = [preText, rule.getSpeechCommand(), postText]
            else:
                utterance = [preText] + [rule.getSpeechCommand()] * 3 + [postText]
            speech.cancelSpeech()
            speech.speak(utterance)
        finally:
            rulesDialogOpen = True

    def getBiwCategories(self):
        soundsPath = getSoundsPath()
        return [o for o in os.listdir(soundsPath)
            if os.path.isdir(os.path.join(soundsPath,o))
        ]

    def getBuiltInWaveFilesInCategory(self):
        soundsPath = getSoundsPath()
        category = self.getBiwCategory()
        ext = ".wav"
        return [o for o in os.listdir(os.path.join(soundsPath, category))
            if not os.path.isdir(os.path.join(soundsPath,o))
                and o.lower().endswith(ext)
        ]

    def getBuiltInWaveFiles(self):
        soundsPath = getSoundsPath()
        result = []
        for dirName, subdirList, fileList in os.walk(soundsPath, topdown=True):
            relDirName = dirName[len(soundsPath):]
            if len(relDirName) > 0 and relDirName[0] == "\\":
                relDirName = relDirName[1:]
            for fileName in fileList:
                if fileName.lower().endswith(".wav"):
                    result.append(os.path.join(relDirName, fileName))
        return result

    def getBiw(self):
        return os.path.join(
            self.getBiwCategory(),
            self.getBuiltInWaveFilesInCategory()[self.biwList.control.GetSelection()]
        )

    def setBiw(self, biw):
        category, biwFile = os.path.split(biw)
        categoryIndex = self.getBiwCategories().index(category)
        self.biwCategory.control.SetSelection(categoryIndex)
        self.onBiwCategory(None)
        biwIndex = self.getBuiltInWaveFilesInCategory().index(biwFile)
        self.biwList.control.SetSelection(biwIndex)

    def onBiw(self, evt):
        soundsPath = getSoundsPath()
        biw = self.getBiw()
        fullPath = os.path.join(soundsPath, biw)
        nvwave.playWaveFile(fullPath)

    def getBiwCategory(self):
        return   self.getBiwCategories()[self.biwCategory.control.GetSelection()]

    def onBiwCategory(self, evt):
        soundsPath = getSoundsPath()
        category = self.getBiwCategory()
        self.biwList.control.SetItems(self.getBuiltInWaveFilesInCategory())

    def onType(self, evt):
        [control.Disable() for (t,controls) in self.typeControls.items() for control in controls]
        ct = self.getType()
        [control.Enable() for control in self.typeControls[ct]]

class RulesListDialog(
    gui.dpiScalingHelper.DpiScalingHelperMixinWithoutInit,
    wx.Dialog,
):
    def __init__(self, parent, site):
        title=_("Edit rules for %s") % site.getDisplayName()
        super(RulesListDialog,self).__init__(parent,title=title)
        self.site = site
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
      # Rules table
        rulesText = _("&Rules")
        self.rulesList = sHelper.addLabeledControl(
            rulesText,
            nvdaControls.AutoWidthColumnListCtrl,
            autoSizeColumn=2,
            itemTextCallable=self.getItemTextForList,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL
        )

        self.rulesList.InsertColumn(0, _("Name"), width=self.scaleSize(150))
        self.rulesList.InsertColumn(1, _("Pattern"))
        self.rulesList.InsertColumn(2, _("Match type"))
        self.rulesList.InsertColumn(3, _("Category"))
        self.rulesList.InsertColumn(4, _("Enabled"))
        self.rulesList.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.onListItemFocused)
        self.rulesList.ItemCount = len(self.site.rules)

        bHelper = sHelper.addItem(guiHelper.ButtonHelper(orientation=wx.HORIZONTAL))
      # Buttons
        self.addButton = bHelper.addButton(self, label=_("&Add"))
        self.addButton.Bind(wx.EVT_BUTTON, self.OnAddClick)
        self.editButton = bHelper.addButton(self, label=_("&Edit"))
        self.editButton.Bind(wx.EVT_BUTTON, self.OnEditClick)
        self.removeButton = bHelper.addButton(self, label=_("&Remove rule"))
        self.removeButton.Bind(wx.EVT_BUTTON, self.OnRemoveClick)
        self.moveUpButton = bHelper.addButton(self, label=_("Move &up"))
        self.moveUpButton.Bind(wx.EVT_BUTTON, lambda evt: self.OnMoveClick(evt, -1))
        self.moveDownButton = bHelper.addButton(self, label=_("Move &down"))
        self.moveDownButton.Bind(wx.EVT_BUTTON, lambda evt: self.OnMoveClick(evt, 1))
        self.sortButton = bHelper.addButton(self, label=_("&Sort"))
        self.sortButton.Bind(wx.EVT_BUTTON, self.OnSortClick)
      # OK/Cancel buttons
        sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))

    def postInit(self):
        self.rulesList.SetFocus()

    def getItemTextForList(self, item, column):
        rule = self.site.rules[item]
        if column == 0:
            return rule.getDisplayName()
        elif column == 1:
            return rule.pattern
        elif column == 2:
            return patterMatchNames[rule.patternMatch]
        elif column == 3:
            return ruleCategoryNames[rule.category]
        elif column == 4:
            return _('Enabled') if rule.enabled else _('Disabled')
        else:
            raise ValueError("Unknown column: %d" % column)

    def onListItemFocused(self, evt):
        if self.rulesList.GetSelectedItemCount()!=1:
            return
        index=self.rulesList.GetFirstSelected()
        rule = self.site.rules[index]

    def OnAddClick(self,evt):
        entryDialog=EditSiteDialog(self)
        if entryDialog.ShowModal()==wx.ID_OK:
            self.site.rules.append(entryDialog.rule)
            self.rulesList.ItemCount = len(self.site.rules)
            index = self.rulesList.ItemCount - 1
            self.rulesList.Select(index)
            self.rulesList.Focus(index)
            # We don't get a new focus event with the new index.
            self.rulesList.sendListItemFocusedEvent(index)
            self.rulesList.SetFocus()
            entryDialog.Destroy()

    def OnEditClick(self,evt):
        if self.rulesList.GetSelectedItemCount()!=1:
            return
        editIndex=self.rulesList.GetFirstSelected()
        if editIndex<0:
            return
        entryDialog=EditSiteDialog(
            self,
            site=self.site.rules[editIndex],
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            self.site.rules[editIndex] = entryDialog.rule
            self.rulesList.SetFocus()
        entryDialog.Destroy()

    def OnRemoveClick(self,evt):
        index=self.rulesList.GetFirstSelected()
        while index>=0:
            self.rulesList.DeleteItem(index)
            del self.site.rules[index]
            index=self.rulesList.GetNextSelected(index)
        self.rulesList.SetFocus()

    def OnMoveClick(self,evt, increment):
        if self.rulesList.GetSelectedItemCount()!=1:
            return
        index=self.rulesList.GetFirstSelected()
        if index<0:
            return
        newIndex = index + increment
        if 0 <= newIndex < len(self.site.rules):
            # Swap
            tmp = self.site.rules[index]
            self.site.rules[index] = self.site.rules[newIndex]
            self.site.rules[newIndex] = tmp
            self.rulesList.Select(newIndex)
            self.rulesList.Focus(newIndex)
        else:
            return

    def OnSortClick(self,evt):
        self.site.rules.sort(key=QJSite.getDisplayName)

    def onOk(self,evt):
        evt.Skip()

class EditSiteDialog(wx.Dialog):
    def __init__(self, parent, site=None, knownSites=None):
        title=_("Edit site configuration")
        super(EditSiteDialog,self).__init__(parent,title=title)
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        if site is  not None:
            self.site = site
        else:
            self.site = QJSite({
                'domain':'',
                'name':'',
                'urlMatch':URLMatch.SUBDOMAIN.value,
                'focusMode':FocusMode.UNCHANGED.value
            })
        self.knownSites = knownSites

      # Translators: domain
        patternLabelText = _("&URL")
        self.patternTextCtrl=sHelper.addLabeledControl(patternLabelText, wx.TextCtrl)
        self.patternTextCtrl.SetValue(self.site.domain)
      # Translators:  label for type selector radio buttons
        typeText = _("&Match type")
        typeChoices = [urlMatchNames[i] for i in URLMatch]
        self.typeRadioBox=sHelper.addItem(wx.RadioBox(self,label=typeText, choices=typeChoices))
        self.typeRadioBox.SetSelection(self.site.urlMatch.value)

      # Translators: label for comment edit box
        commentLabelText = _("&Display name (optional)")
        self.commentTextCtrl=sHelper.addLabeledControl(commentLabelText, wx.TextCtrl)
        self.commentTextCtrl.SetValue(self.site.name)
      # Edit Rules button
        self.editRulesButton = sHelper.addItem (wx.Button (self, label = _("Edit R&ules")))
        self.editRulesButton.Bind(wx.EVT_BUTTON, self.OnEditRulesClick)

      # Translators: Focus Mode comboBox
        focusModeLabelText=_("&Focus mode")
        self.focusModeCategory=guiHelper.LabeledControlHelper(
            self,
            focusModeLabelText,
            wx.Choice,
            choices=[
                focusModeNames[m]
                for m in FocusMode
            ],
        )
        self.focusModeCategory.control.SetSelection(self.site.focusMode.value)
      #  OK/cancel buttons
        sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))

        mainSizer.Add(sHelper.sizer,border=20,flag=wx.ALL)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        self.patternTextCtrl.SetFocus()
        self.Bind(wx.EVT_BUTTON,self.onOk,id=wx.ID_OK)

    def make(self):
        urlMatch = URLMatch(self.typeRadioBox.GetSelection())
        domain = self.patternTextCtrl.Value
        errorMsg = None
        if urlMatch == URLMatch.IGNORE:
            if len(domain) > 0:
                errorMsg = _("You must specify blank domain in order to match all sites.")
        else:
            if len(domain) == 0:
                errorMsg = _("You must specify non-empty string as domain")
            elif urlMatch in [URLMatch.DOMAIN, URLMatch.SUBDOMAIN]:
                m = re.match(r'[\w.-]+(:\d+)?', domain)
                if not m:
                    errorMsg = _("Wrong domain format. An example is: en.wikipedia.com ")
            elif urlMatch == URLMatch.REGEX:
                try:
                    re.compile(domain)
                except re.error:
                    errorMsg = _("Failed to compile regular expression!")

        if errorMsg is None and self.knownSites is not None:
            for other in self.knownSites:
                if (
                    domain == other.domain
                    and urlMatch == other.urlMatch
                ):
                    errorMsg = (
                        _("This site is a duplicate of another existing site %s")
                        % other.getDisplayName()
                    )
        if errorMsg is not None:
            # Translators: This is an error message to let the user know that the pattern field is not valid.
            gui.messageBox(errorMsg, _("Dictionary Entry Error"), wx.OK|wx.ICON_WARNING, self)
            self.patternTextCtrl.SetFocus()
            return
        if urlMatch != URLMatch.REGEX:
            domain = domain.lower()
        site = QJSite({
            'domain':domain,
            'urlMatch':urlMatch,
            'name':self.commentTextCtrl.Value,
            'focusMode': self.focusModeCategory.control.GetSelection(),
        })
        return site

    def OnEditRulesClick(self,evt):
        entryDialog=RulesListDialog(
            self,
            site=self.site,
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            self.site.rules = entryDialog.site.rules
        entryDialog.Destroy()

    def onOk(self,evt):
        site = self.make()
        if site is not None:
            self.site = site
            evt.Skip()


class SettingsDialog(SettingsPanel):
    title = _("BrowserNav QuickSearch and AutoSkip rules")

    def __init__(self, *args, **kwargs):
        super(SettingsDialog, self).__init__(*args, **kwargs)

    def makeSettings(self, settingsSizer):
        global config
        self.config = copy.deepcopy(config)

        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
      # Sites table
        sitesText = _("&Sites")
        self.sitesList = sHelper.addLabeledControl(
            sitesText,
            nvdaControls.AutoWidthColumnListCtrl,
            autoSizeColumn=2,
            itemTextCallable=self.getItemTextForList,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL
        )

        self.sitesList.InsertColumn(0, _("Name"), width=self.scaleSize(150))
        self.sitesList.InsertColumn(1, _("Domain"))
        self.sitesList.InsertColumn(2, _("Type"))
        self.sitesList.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.onListItemFocused)
        self.sitesList.ItemCount = len(self.config.sites)

        bHelper = sHelper.addItem(guiHelper.ButtonHelper(orientation=wx.HORIZONTAL))
      # Buttons
        self.addButton = bHelper.addButton(self, label=_("&Add"))
        self.addButton.Bind(wx.EVT_BUTTON, self.OnAddClick)
        self.editButton = bHelper.addButton(self, label=_("&Edit site"))
        self.editButton.Bind(wx.EVT_BUTTON, self.OnEditClick)
        self.editRulesButton = bHelper.addButton(self, label=_("Edit R&ules"))
        self.editRulesButton.Bind(wx.EVT_BUTTON, self.OnEditRulesClick)
        self.removeButton = bHelper.addButton(self, label=_("&Remove rule"))
        self.removeButton.Bind(wx.EVT_BUTTON, self.OnRemoveClick)
        self.moveUpButton = bHelper.addButton(self, label=_("Move &up"))
        self.moveUpButton.Bind(wx.EVT_BUTTON, lambda evt: self.OnMoveClick(evt, -1))
        self.moveDownButton = bHelper.addButton(self, label=_("Move &down"))
        self.moveDownButton.Bind(wx.EVT_BUTTON, lambda evt: self.OnMoveClick(evt, 1))
        self.sortButton = bHelper.addButton(self, label=_("&Sort"))
        self.sortButton.Bind(wx.EVT_BUTTON, self.OnSortClick)

    def postInit(self):
        self.sitesList.SetFocus()

    def getItemTextForList(self, item, column):
        site = self.config.sites[item]
        if column == 0:
            return site.getDisplayName()
        elif column == 2:
            return urlMatchNames[site.urlMatch]
        elif column == 1:
            return site.domain
        else:
            raise ValueError("Unknown column: %d" % column)

    def onListItemFocused(self, evt):
        if self.sitesList.GetSelectedItemCount()!=1:
            return
        index=self.sitesList.GetFirstSelected()
        site = self.config.sites[index]

    def OnAddClick(self,evt):
        entryDialog=EditSiteDialog(self, knownSites=self.config.sites)
        if entryDialog.ShowModal()==wx.ID_OK:
            self.config.sites.append(entryDialog.site)
            self.sitesList.ItemCount = len(self.config.sites)
            index = self.sitesList.ItemCount - 1
            self.sitesList.Select(index)
            self.sitesList.Focus(index)
            # We don't get a new focus event with the new index.
            self.sitesList.sendListItemFocusedEvent(index)
            self.sitesList.SetFocus()
            entryDialog.Destroy()

    def OnEditClick(self,evt):
        if self.sitesList.GetSelectedItemCount()!=1:
            return
        editIndex=self.sitesList.GetFirstSelected()
        if editIndex<0:
            return
        entryDialog=EditSiteDialog(
            self,
            site=self.config.sites[editIndex],
            knownSites=self.config.sites[:editIndex] + self.config.sites[editIndex+1:],
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            self.config.sites[editIndex] = entryDialog.site
            self.sitesList.SetFocus()
        entryDialog.Destroy()

    def OnEditRulesClick(self,evt):
        if self.sitesList.GetSelectedItemCount()!=1:
            return
        editIndex=self.sitesList.GetFirstSelected()
        if editIndex<0:
            return
        entryDialog=RulesListDialog(
            self,
            site=self.config.sites[editIndex],
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            self.config.sites[editIndex].rules = entryDialog.site.rules
            self.sitesList.SetFocus()
        entryDialog.Destroy()

    def OnRemoveClick(self,evt):
        index=self.sitesList.GetFirstSelected()
        while index>=0:
            self.sitesList.DeleteItem(index)
            del self.config.sites[index]
            index=self.sitesList.GetNextSelected(index)
        self.sitesList.SetFocus()

    def OnMoveClick(self,evt, increment):
        if self.sitesList.GetSelectedItemCount()!=1:
            return
        index=self.sitesList.GetFirstSelected()
        if index<0:
            return
        newIndex = index + increment
        if 0 <= newIndex < len(self.config.sites):
            # Swap
            tmp = self.config.sites[index]
            self.config.sites[index] = self.config.sites[newIndex]
            self.config.sites[newIndex] = tmp
            self.sitesList.Select(newIndex)
            self.sitesList.Focus(newIndex)
        else:
            return

    def OnSortClick(self,evt):
        self.config.sites.sort(key=QJSite.getDisplayName)

    def onSave(self):
        global config
        config = self.config
        saveConfig()
