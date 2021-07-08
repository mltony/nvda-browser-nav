#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import  dataclasses
from enum import Enum
import globalVars
import gui
from gui.settingsDialogs import SettingsPanel
import os
import wx

class RuleCategory(Enum):
    UNKNOWN = 0
    SEARCH = 1
    HIDE = 2

ruleCategoryNames = {
    RuleCategory.SEARCH: _('QuickSearch'),
    RuleCategory.HIDE: _('AutoHide'),
}

class URLMatch(Enum):
    IGNORE = 0
    DOMAIN = 1
    SUBDOMAIN = 2
    SUBSTRING = 3
    EXACT = 4
    REGEX = 5

urlMatchNames = {
    URLMatch.IGNORE: _('Ignore'),
    URLMatch.DOMAIN: _('Match domain name'),
    URLMatch.SUBDOMAIN: _('Match domain and its subdomains'),
    URLMatch.SUBSTRING: _('Match substring in URL'),
    URLMatch.EXACT: _('Exact URL match'),
    URLMatch.REGEX: _('Regex match of URL'),
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

@dataclasses.dataclass
class Rule:
    enabled: bool
    category: RuleCategory
    name: str
    domain: str
    urlMatch: URLMatch
    pattern: str
    patternMatch: PatternMatch

    def postLoad(self):
        self.category = RuleCategory(self.category)
        self.urlMatch = URLMatch(self.urlMatch)
        self.patternMatch = PatternMatch(self.patternMatch)
        return self

    def getDisplayName(self):
        if self.name is not None and len(self.name) > 0:
            return self.name
        return self.pattern

rules = []
rulesFileName = os.path.join(globalVars.appArgs.configPath, "browserNavRules.json")

defaultRulesFileName = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "browserNavRules.json"
)
def loadRules():
    global rules
    try:
        rulesConfig = open(rulesFileName, "r").read()
    except FileNotFoundError:
        rulesConfig = open(defaultRulesFileName, "r").read()
    rules = [
        Rule(**rule).postLoad()
        for rule in json.loads(rulesConfig)['rules']
    ]

def saveRules(rules):
    rulesDicts = [
        dataclasses.asdict(rule)
        for rule in rules
    ]
    rulesJson = json.dumps({'rules': rulesDicts}, indent=4, sort_keys=True)
    rulesFile = open(rulesFileName, "w")
    try:
        rulesFile.write(rulesJson)
    finally:
        rulesFile.close()
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

class SettingsDialog(SettingsPanel):
    title = _("BrowserNav QuickSearch and AutoSkip rules")

    def __init__(self, *args, **kwargs):
        super(SettingsDialog, self).__init__(*args, **kwargs)
        self.rules = rules[:]
        self.refresh()


    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
      # Rules table
        rulesText = _("&Rules")
        self.rulesList = sHelper.addLabeledControl(
            rulesText,
            nvdaControls.AutoWidthColumnListCtrl,
            autoSizeColumn=2,
            itemTextCallable=self.getItemTextForList,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL
        )

        self.rulesList.InsertColumn(0, _("Pattern"), width=self.scaleSize(150))
        self.rulesList.InsertColumn(1, _("Status"))
        self.rulesList.InsertColumn(2, _("Type"))
        self.rulesList.InsertColumn(3, _("Domain"))
        self.rulesList.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.onListItemFocused)
        self.rulesList.ItemCount = len(self.rules)
      # Buttons
        bHelper = sHelper.addItem(guiHelper.ButtonHelper(orientation=wx.HORIZONTAL))
        self.toggleButton = bHelper.addButton(self, label=_("Toggle"))
        self.toggleButton.Bind(wx.EVT_BUTTON, self.onToggleClick)
        self.addAudioButton = bHelper.addButton(self, label=_("&Add"))
        self.addAudioButton.Bind(wx.EVT_BUTTON, self.OnAddClick)
        self.editButton = bHelper.addButton(self, label=_("&Edit"))
        self.editButton.Bind(wx.EVT_BUTTON, self.OnEditClick)
        self.removeButton = bHelper.addButton(self, label=_("&Remove rule"))
        self.removeButton.Bind(wx.EVT_BUTTON, self.OnRemoveClick)

    def postInit(self):
        self.rulesList.SetFocus()

    def getItemTextForList(self, item, column):
        rule = self.displayedRules[item]
        if column == 0:
            return rule.getDisplayName()
        elif column == 1:
            return _("Enabled") if rule.enabled else _("Disabled")
        elif column == 2:
            return ruleCategoryNames[rule.category]
        elif column == 3:
            return rule.domain
        else:
            raise ValueError("Unknown column: %d" % column)

    def onListItemFocused(self, evt):
        if self.rulesList.GetSelectedItemCount()!=1:
            return
        index=self.rulesList.GetFirstSelected()
        rule = self.displayedRules[index]
        if rule.enabled:
            self.toggleButton.SetLabel(_("Disable (&toggle)"))
        else:
            self.toggleButton.SetLabel(_("Enable (&toggle)"))

    def refresh(self):
        self.displayedRules = self.rules[:]


    def onSave(self):
        super(SettingsDialog, self).onOk(evt)


