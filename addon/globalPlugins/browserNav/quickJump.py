#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2022 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import api
import browseMode
from collections import namedtuple, defaultdict
from contextlib import ExitStack
import controlTypes
from controlTypes import OutputReason
import copy
import core
import dataclasses
from dataclasses import dataclass
import diffHandler
import difflib as dl
from enum import Enum
import functools
import globalVars
import gui
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import SettingsPanel
import inputCore
import itertools
import json
from logHandler import log
import math
import os
import re
import textInfos
import threading
import time
import tones
from typing import List, Tuple
import ui
import weakref
import wx
import addonHandler
addonHandler.initTranslation()

sonifyTextInfo = None # Due to import error we set this value from __init__

from .constants import *
from . beeper import *
from . import utils
from .editor import EditTextDialog
from .paragraph import Paragraph, NotFoundError, ScriptError, textInfoRange, pump, retry, getFocusTextInfo, getFocusParagraph
import types
import ast
import inspect

try:
    REASON_CARET = controlTypes.REASON_CARET
except AttributeError:
    REASON_CARET = controlTypes.OutputReason.CARET



debug = False
if debug:
    def mylog(s):
        if debug:
            f = open("C:\\Users\\tony\\od\\2.txt", "a", encoding='utf-8')
            print(str(s), file=f)
            f.flush()
            f.close()
else:
    def mylog(s):
        pass


class QuickJumpScriptException(Exception):
    pass

class QuickJumpMatchPerformedException(Exception):
    pass

class BookmarkCategory(Enum):
    QUICK_JUMP = 1
    QUICK_JUMP_2 = 2
    QUICK_JUMP_3 = 3
    SKIP_CLUTTER = 4
    QUICK_CLICK = 5
    QUICK_CLICK_2 = 6
    QUICK_CLICK_3 = 7
    HIERARCHICAL = 8
    QUICK_SPEAK = 9
    QUICK_SPEAK_2 = 10
    SCRIPT = 11
    NUMERIC_SCRIPT = 12

BookmarkCategoryShortNames = {
    BookmarkCategory.QUICK_JUMP: _('QuickJump'),
    BookmarkCategory.QUICK_JUMP_2: _('QuickJump2'),
    BookmarkCategory.QUICK_JUMP_3: _('QuickJump3'),
    BookmarkCategory.SKIP_CLUTTER: _('SkipClutter'),
    BookmarkCategory.QUICK_CLICK: _('QuickClick'),
    BookmarkCategory.QUICK_CLICK_2: _('QuickClick2'),
    BookmarkCategory.QUICK_CLICK_3: _('QuickClick3'),
    BookmarkCategory.HIERARCHICAL: _('Hierarchical quick jump'),
    BookmarkCategory.QUICK_SPEAK: _('Quick speak'),
    BookmarkCategory.QUICK_SPEAK_2: _('Quick speak 2'),
    BookmarkCategory.SCRIPT: _('Script'),
    BookmarkCategory.NUMERIC_SCRIPT: _('Numeric Script'),
}

BookmarkCategoryNames = {
    BookmarkCategory.QUICK_JUMP: _('QuickJump - assigned to J by default'),
    BookmarkCategory.QUICK_JUMP_2: _('QuickJump2'),
    BookmarkCategory.QUICK_JUMP_3: _('QuickJump3'),
    BookmarkCategory.SKIP_CLUTTER: _('SkipClutter - will automatically skip this paragraph or line when navigating via Control+Up/Down or Up/Down keystrokes; must match the whole paragraph. or '),
    BookmarkCategory.QUICK_CLICK: _('QuickClick'),
    BookmarkCategory.QUICK_CLICK_2: _('QuickClick2'),
    BookmarkCategory.QUICK_CLICK_3: _('QuickClick3'),
    BookmarkCategory.HIERARCHICAL: _('Hierarchical quick jump'),
    BookmarkCategory.QUICK_SPEAK: _('Quick speak'),
    BookmarkCategory.QUICK_SPEAK_2: _('Quick speak 2'),
    BookmarkCategory.SCRIPT: _('Script: runs a custom Python script'),
    BookmarkCategory.NUMERIC_SCRIPT: _('Numeric Script - script that can consume a numeric argument by pressing Alt+digits'),
}

class URLMatch(Enum):
    IGNORE = 0
    DOMAIN = 1
    SUBDOMAIN = 2
    SUBSTRING = 3
    EXACT = 4
    REGEX = 5
    EMPTY = 6

urlMatchNames = {
    URLMatch.IGNORE: _('Match all sites (domain field ignored) '),
    URLMatch.DOMAIN: _('Match domain name'),
    URLMatch.SUBDOMAIN: _('Match domain and its subdomains'),
    URLMatch.SUBSTRING: _('Match substring in URL'),
    URLMatch.EXACT: _('Exact URL match'),
    URLMatch.REGEX: _('Regex match of URL'),
    URLMatch.EMPTY: _('Match empty URL only, that is pages without URL'),
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

class LiveRegionMode(Enum):
    UNCHANGED = 0
    MUTE_LIVE_REGION = 1


liveRegionModeNames = {
    LiveRegionMode.UNCHANGED: _("Speak live regions"),
    LiveRegionMode.MUTE_LIVE_REGION: _("Mute live regions"),
}

class DebugBeepMode(Enum):
    NO_BEEPS = 0
    ON_FOCUS = 1
    ON_AUTO_CLICK = 2
    ON_LIVE_REGION = 3

debugBeepModeNames = {
    DebugBeepMode.NO_BEEPS: _("No beeps"),
    DebugBeepMode.ON_FOCUS: _("Beep on every focus event"),
    DebugBeepMode.ON_AUTO_CLICK: _("Beep on every successful autoClick"),
    DebugBeepMode.ON_LIVE_REGION: _("Beep on every update from live region"),
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

class ParagraphAttribute(Enum):
    ROLE = 'role'
    HEADING = 'heading'
    FONT_SIZE = 'font-size'
    FONT_FAMILY = 'font-family'
    COLOR = 'color'
    BACKGROUND_COLOR = 'background-color'
    BOLD = 'bold'
    ITALIC = 'italic'

class AutoSpeakMode(Enum):
    OFF = 'off'
    PARAGRAPH_DIFF = 'paragraph_diff'
    WORD_DIFF = 'word_diff'
    CHIME_ON_ADD = 'chime_on_add'
    CHIME_ON_REMOVE = 'chime_on_remove'
    CHIME_ON_CHANGE = 'chime_on_change'

autoSpeakModeNames = {
    AutoSpeakMode.OFF: _("AutoSpeak disabled"),
    AutoSpeakMode.PARAGRAPH_DIFF: _("Speak changed paragraphs"),
    AutoSpeakMode.WORD_DIFF: _("Speak only changed words (diff)"),
    AutoSpeakMode.CHIME_ON_ADD: _("Play chime when bookmark appears on the page"),
    AutoSpeakMode.CHIME_ON_REMOVE: _("Play chime when bookmark disappears from the page"),
    AutoSpeakMode.CHIME_ON_CHANGE: _("Play chime when text matched by bookmark changes"),

}
class QJImmutable:
    def __init__(self):
        object.__setattr__(self, 'frozen', False)

    def freeze(self):
        self.frozen = True

    def __setattr__(self, *args):
        if self.frozen:
            raise TypeError
        return super(QJImmutable, self).__setattr__( *args)

    def __delattr__(self, *args):
        if self.frozen:
            raise TypeError
        return super(QJImmutable, self).__delattr__( *args)


@functools.total_ordering
class QJAttribute(QJImmutable):
    attribute: ParagraphAttribute
    value: any

    def __init__(
        self,
        d=None,
        role=None,
        heading=None,
        userString=None,
    ):
        if d is not None:
            object.__setattr__(self, 'attribute', ParagraphAttribute(d['attribute']))
            value = d['value']
            if self.attribute == ParagraphAttribute.ROLE:
                try:
                    textValue = utils.NVDA2021Role(value).name
                except ValueError:
                    textValue = value
                value = getattr(controlTypes.Role, textValue)
            object.__setattr__(self, 'value', value)
        elif userString is not None:
            s = userString.strip()
            tokens = s.split(":")
            if len(tokens) != 2:
                raise ValueError(f"Invalid format of attribute! After splitting by : found {len(tokens)} tokens, but expected 2. userString='{s}'")
            try:
                object.__setattr__(self, 'attribute', ParagraphAttribute(tokens[0].lower()))
            except ValueError as e:
                raise ValueError(f"Invalid attribute {tokens[0]}. User string='{userString}'.", e)
            if self.attribute == ParagraphAttribute.ROLE:
                roleName = tokens[1].lower()
                try:
                    value = controlTypes.role.Role.__getattr__(roleName.upper())
                except AttributeError:
                    raise ValueError(f"Invalid role '{roleName}'.")
            else:
                value = tokens[1]
            object.__setattr__(self, 'value', value)
        elif role is not None:
            object.__setattr__(self, 'attribute', ParagraphAttribute.ROLE)
            object.__setattr__(self, 'value', role)
        elif heading is not None:
            object.__setattr__(self, 'attribute', ParagraphAttribute.HEADING)
            object.__setattr__(self, 'value', heading)
        else:
            raise Exception("Impossible!")


    def asDict(self):
        return {
            'attribute': self.attribute.value,
            'value': self.value.name if self.attribute == ParagraphAttribute.ROLE else self.value,

        }


    def asString(self):
        if self.attribute == ParagraphAttribute.ROLE:
            value = self.value.name
        else:
            value = self.value
        return f"{self.attribute.value}:{value}"

    def __members(self):
        return (self.attribute.value, self.value)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__members() == other.__members()
        else:
            return False

    def __hash__(self):
        return hash(self.__members())

    def __lt__(self, other):
        if type(other) is type(self):
            return self.__members() < other.__members()
        else:
            return False


class QJAttributeMatch(QJImmutable):
    invert: bool
    attribute: QJAttribute

    def __init__(
        self,
        d=None,
        userString=None
    ):
        if d is not None:
            object.__setattr__(self, 'invert', d['invert'])
            object.__setattr__(self, 'attribute', QJAttribute(d['attribute']))
        elif userString is not None:
            s = userString.strip()
            if len(s) == 0:
                raise ValueError("Empty string!")
            object.__setattr__(self, 'invert', s.startswith("!"))
            if s.startswith("!"):
                s = s[1:]
            object.__setattr__(self, 'attribute', QJAttribute(userString=s))
        else:
            raise Exception("Impossible!")


    def asDict(self):
        return {
            'invert': self.invert,
            'attribute': self.attribute.asDict(),
        }


    def asString(self):
        invertString = "!" if self.invert else ""
        return f"{invertString}{self.attribute.asString()}"

    def __hash__(self):
        return id(self)

    def matches(self, attributes):
        if not self.invert:
            return self.attribute in attributes
        else:
            return self.attribute not in attributes

def indentPythonCode(code, level):
    result = []
    for line in code.splitlines():
        line = line.rstrip("\r\n")
        indentLength = len(line) - len(line.lstrip(' \t'))
        indentStr = line[:indentLength]
        line = line[indentLength:]
        indentStr = indentStr.replace('\t', '    ')
        indent = len(indentStr)
        result.append(' ' * (indent + level) + (line))
    return "\n".join(result)

PYTHOS_SCRIPT_TEMPLATE = indentPythonCode("""
    def quickJumpScript(p=None, t=None, match=None, level=None, modifiers=None):
    {indentedCode}

""".lstrip(), -4)

def wrapPythonCode(code):
    return PYTHOS_SCRIPT_TEMPLATE.format(
        indentedCode=indentPythonCode(code, 4)
    )

safe_builtins = {
    s: __builtins__[s]
    for s in "__import__ abs all any ascii bin chr dir divmod format hash hex id isinstance issubclass iter len max min next oct ord pow repr round sorted sum None Ellipsis NotImplemented False True bool bytearray bytes complex dict enumerate filter float frozenset int list map object range reversed set slice str tuple type zip BaseException Exception TypeError StopAsyncIteration StopIteration GeneratorExit SystemExit KeyboardInterrupt ImportError ModuleNotFoundError OSError EnvironmentError IOError WindowsError EOFError RuntimeError RecursionError NotImplementedError NameError UnboundLocalError AttributeError SyntaxError IndentationError TabError LookupError IndexError KeyError ValueError UnicodeError UnicodeEncodeError UnicodeDecodeError UnicodeTranslateError AssertionError ArithmeticError FloatingPointError OverflowError ZeroDivisionError SystemError ReferenceError MemoryError BufferError ConnectionError BlockingIOError BrokenPipeError ChildProcessError ConnectionAbortedError ConnectionRefusedError ConnectionResetError FileExistsError FileNotFoundError IsADirectoryError NotADirectoryError InterruptedError PermissionError ProcessLookupError TimeoutError".split()
}

execGlobals = {
    '__builtins__': safe_builtins,
    'Paragraph': Paragraph,
    'NotFoundError': NotFoundError,
    'ScriptError': ScriptError,
    'pump': pump,
    'retry': retry,
    'getFocusTextInfo': getFocusTextInfo,
    'getFocusParagraph': getFocusParagraph,
    'textInfoRange': textInfoRange,
    'ParagraphAttribute': ParagraphAttribute,
    'itertools': itertools,
    'math': math,
    'log': log,
    'operator': operator,
    'print': log.info,
    're': re,
    'api': api,
    'controlTypes': controlTypes,
    'speech': speech,
    'textInfos': textInfos,
    'tones': tones,
    'types': types,
    'ui': ui,
}

EMPTY_PYTHON_LINE_REGEXP = re.compile("^\s*(#.*)?$")
class QJBookmark(QJImmutable):
    enabled: bool
    category: BookmarkCategory
    name: str
    pattern: str
    patternMatch: PatternMatch
    attributes: Tuple[QJAttributeMatch]
    message: str
    offset: int
    snippet: str
    alsoUseDefaultQuickJump: bool
    keystroke: str
    enableAutoSpeak: bool
    autoSpeakMode: AutoSpeakMode
    builtInWavFile: str

    def __init__(self, d):
        object.__setattr__(self, 'enabled', d['enabled'])
        object.__setattr__(self, 'category', BookmarkCategory(d['category']))
        object.__setattr__(self, 'name', d['name'])
        object.__setattr__(self, 'pattern', d['pattern'])
        object.__setattr__(self, 'patternMatch', PatternMatch(d['patternMatch']))
        object.__setattr__(self, 'attributes', tuple([
            QJAttributeMatch(attrDict)
            for attrDict in d['attributes']
        ]))
        object.__setattr__(self, 'message', d['message'])
        object.__setattr__(self, 'offset', d['offset'])
        object.__setattr__(self, 'snippet', d.get('snippet', ''))
        compileError = None
        bytecode = None
        scriptFunc = None
        if not self.isSnippetEmpty():
            execLocals = {}
            try:
                compiled = compile(wrapPythonCode(self.snippet), "<bookmarkScript>", 'exec', ast.PyCF_ONLY_AST)
                ast.increment_lineno(compiled, -1)
                bytecode = compile(compiled, "<bookmarkScript>", 'exec', dont_inherit=True)
                exec(bytecode, execGlobals, execLocals)
                scriptFunc = execLocals['quickJumpScript']
                #bytecode = compile(wrapPythonCode(self.snippet), "<bookmarkScript>", "exec")
            except SyntaxError as e:
                compileError = e
        object.__setattr__(self, 'bytecode', bytecode)
        object.__setattr__(self, 'scriptFunc', scriptFunc)
        object.__setattr__(self, 'compileError', compileError)
        object.__setattr__(self, 'alsoUseDefaultQuickJump', d.get('alsoUseDefaultQuickJump', False))
        object.__setattr__(self, 'keystroke', d.get('keystroke', None))
        object.__setattr__(self, 'enableAutoSpeak', d.get('enableAutoSpeak', False))
        object.__setattr__(self, 'autoSpeakMode', AutoSpeakMode(d.get('autoSpeakMode', AutoSpeakMode.OFF.value)))
        object.__setattr__(self, 'builtInWavFile', d.get('builtInWavFile', None))

    def asDict(self):
        return {
            'enabled': self.enabled,
            'category': self.category.value,
            'name': self.name,
            'pattern': self.pattern,
            'patternMatch': self.patternMatch.value,
            'attributes': [
                attr.asDict()
                for attr in self.attributes
            ],
            'message': self.message,
            'offset': self.offset,
            'snippet': self.snippet,
            'alsoUseDefaultQuickJump': self.alsoUseDefaultQuickJump,
            'keystroke': self.keystroke,
            'enableAutoSpeak': self.enableAutoSpeak,
            'autoSpeakMode': self.autoSpeakMode.value,
            'builtInWavFile': self.builtInWavFile,
        }

    def getDisplayName(self):
        if self.name is not None and len(self.name) > 0:
            return self.name
        return self.pattern

    def isSnippetEmpty(self):
        for line in self.snippet.splitlines():
            if not EMPTY_PYTHON_LINE_REGEXP.search(line.rstrip("\r\n")):
                return False
        return True


    def __hash__(self):
        return id(self)



class QJSite(QJImmutable):
    domain: str
    urlMatch: URLMatch
    name: str
    focusMode: FocusMode
    liveRegionMode: LiveRegionMode
    debugBeepMode: DebugBeepMode
    bookmarks: Tuple[QJBookmark]
    autoClickOnFocus: bool
    autoClickCategory: BookmarkCategory
    autoClickOnFocusDelay: int
    autoClickContinuous: bool
    autoClickContinuousDelay: int
    autoSpeak: bool
    autoSpeakCategory: BookmarkCategory
    suppressDescription: bool

    def __init__(self, d):
        super().__init__()
        self.domain= d['domain']
        self.urlMatch = URLMatch(d['urlMatch'])
        self.name = d['name']
        self.focusMode = FocusMode(d['focusMode'])
        self.liveRegionMode = LiveRegionMode(d['liveRegionMode'])
        self.debugBeepMode = DebugBeepMode(d['debugBeepMode'])
        self.bookmarks = tuple([
            QJBookmark(bookmarkDict)
            for bookmarkDict in d['bookmarks']
        ])
        self.autoClickOnFocus = d['autoClickOnFocus']
        self.autoClickCategory = BookmarkCategory(d['autoClickCategory'])
        self.autoClickOnFocusDelay = d['autoClickOnFocusDelay']
        self.autoClickContinuous = d['autoClickContinuous']
        self.autoClickContinuousDelay = d['autoClickContinuousDelay']
        self.autoSpeak = d.get('autoSpeak', False)
        self.autoSpeakCategory = BookmarkCategory(d.get('autoSpeakCategory', BookmarkCategory.QUICK_SPEAK.value))
        self.suppressDescription = d.get('suppressDescription', False)
        self.freeze()

    def asDict(self):
        return {
            'domain': self.domain,
            'urlMatch': self.urlMatch.value,
            'name': self.name,
            'focusMode': self.focusMode.value,
            'liveRegionMode': self.liveRegionMode.value,
            'debugBeepMode': self.debugBeepMode.value,
            'bookmarks': [bookmark.asDict() for bookmark in self.bookmarks],
            'autoClickOnFocus': self.autoClickOnFocus,
            'autoClickCategory': self.autoClickCategory.value,
            'autoClickOnFocusDelay': self.autoClickOnFocusDelay,
            'autoClickContinuous': self.autoClickContinuous,
            'autoClickContinuousDelay': self.autoClickContinuousDelay,
            'autoSpeak': self.autoSpeak,
            'autoSpeakCategory': self.autoSpeakCategory.value,
            'suppressDescription': self.suppressDescription,
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

    def updateBookmarks(self, bookmarks):
        d = self.asDict()
        d['bookmarks'] = [
            bookmark.asDict()
            for bookmark in bookmarks
        ]
        return QJSite(d)

class QJConfig(QJImmutable):
    sites: Tuple[QJSite]

    def __init__(self, d):
        super().__init__()
        self.sites= tuple([
            QJSite(item)
            for item in d['sites']
        ])
        self.freeze()

    def asDict(self):
        return {
            'sites': [
                site.asDict()
                for site in self.sites
            ],
        }

    def __hash__(self):
        return id(self)

    def updateSites(self, sites):
        d = self.asDict()
        d['sites'] = [
            site.asDict()
            for site in sites
        ]
        return QJConfig(d)

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
    global globalConfig
    configDict = globalConfig.asDict()
    rulesJson = json.dumps(configDict, indent=4, sort_keys=True)
    rulesFile = open(rulesFileName, "w")
    try:
        rulesFile.write(rulesJson)
    finally:
        rulesFile.close()

globalConfig  = loadConfig()


@functools.lru_cache()
def re_compile(s):
    return re.compile(s)

def getDomain(url):
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
        raise ValueError(f"Domain not found in URL {url}")
    domain = m.group('domain').lower()
    return domain


@functools.lru_cache()
def isUrlMatch(url, site):
    if site.urlMatch == URLMatch.IGNORE:
        return True
    elif site.urlMatch in {URLMatch.DOMAIN, URLMatch.SUBDOMAIN}:
        try:
            domain = getDomain(url)
        except ValueError:
            return False
        siteDomain = site.domain.lower()
        if site.urlMatch == URLMatch.DOMAIN:
            return domain == siteDomain
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
        return re_compile(site.domain).search(url) is not None
    elif site.urlMatch == URLMatch.EMPTY:
        return url is None or url == ""
    else:
        raise Exception("Impossible!")

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

def getLiveRegionMode(url, config):
    sites = findSites(url, config)
    if len(sites) == 0:
        return LiveRegionMode.UNCHANGED
    mode = max([
        site.liveRegionMode.value
        for site in sites
    ])
    return LiveRegionMode(mode)


def getDebugBeepModes(url, config):
    sites = findSites(url, config)
    if len(sites) == 0:
        return set()
    return {
        site.debugBeepMode
        for site in sites
    }

def getSuppressDescription(url, config):
    sites = findSites(url, config)
    if len(sites) == 0:
        return False
    mode = max([
        site.suppressDescription
        for site in sites
    ])
    return mode

def getUrlFromObject(object):
    while object is not None:
        try:
            interceptor = object.treeInterceptor
        except AttributeError:
            pass
        if interceptor is not None:
            url = interceptor._get_documentConstantIdentifier()
            if url is not None and len(url) > 0:
                return url
        object = object.simpleParent
urlCache = weakref.WeakKeyDictionary()
def getUrl(self, onlyFromCache=False):
    t0 = time.time()
    urlFromObject = False
    if not onlyFromCache and not isinstance(threading.currentThread(), threading._MainThread):
        raise RuntimeError("Impossible: URL can only be determined from the main thread.")
    if self is None:
        return ""
    if onlyFromCache:
        try:
            return urlCache[self]
        except KeyError:
            return ""
    try:
        try:
            url = self._get_documentConstantIdentifier()
        except AttributeError:
            return ""
        if url is None or len(url) == 0:
            urlFromObject = True
            url = getUrlFromObject(self.currentNVDAObject)
    finally:
        t1 = time.time()
        tt = int(1000 * (t1-t0))
        #mylog(f"getUrl {tt} ms = {url} {urlFromObject}")
        #mylog(str(threading.currentThread()))
    urlCache[self] = url
    if url is None or len(url) == 0:
        return ""
        #future.set("")
    else:
        return url
        #future.set(url)

@functools.lru_cache()
def getBookmarksWithKeystrokesForUrl(url, config, keystroke, category=None):
    sites = findSites(url, config)
    result = []
    for site in sites:
        for bookmark in getBookmarksWithKeystrokesForSite(site).get(keystroke, []):
            if category is None or category == bookmark.category:
                result.append(bookmark)
    return result

@functools.lru_cache()
def getBookmarksWithKeystrokesForSite(site):
    extractKeystrokeFunc = lambda b: b.keystroke or "default"
    return {
        keystroke: list(grouper)
        for keystroke, grouper in itertools.groupby(
            sorted(
                [
                    bookmark
                    for bookmark in site.bookmarks
                    if bookmark.enabled
                ],
                key=extractKeystrokeFunc,
            ),
            key=extractKeystrokeFunc,
        )
    }

@functools.lru_cache()
def getAutoSpeakBookmarksForUrl(url, config):
    sites = findSites(url, config)
    results = [
        bookmark
        for site in sites
        for bookmark in site.bookmarks
        if bookmark.category in {
            BookmarkCategory.QUICK_SPEAK,
            BookmarkCategory.QUICK_SPEAK_2,
        }
        and bookmark.enabled
        and bookmark.autoSpeakMode != AutoSpeakMode.OFF
    ]
    return tuple(results)

originalShouldPassThrough = None
def newShouldPassThrough(self, obj, reason= None):
    focusMode = getFocusMode(getUrl(self), globalConfig)
    if reason == OutputReason.FOCUS and focusMode == FocusMode.DONT_ENTER_FORM_MODE:
        return self.passThrough
    else:
        return originalShouldPassThrough(self, obj, reason)

original_event_gainFocus = None
def new_event_gainFocus(self, obj, nextHandler):
    url = getUrl(self)
    if DebugBeepMode.ON_FOCUS in getDebugBeepModes(url, globalConfig):
        tones.beep(500, 50)
    focusMode = getFocusMode(url, globalConfig)
    if focusMode == FocusMode.DISABLE_FOCUS:
        return nextHandler()
    return original_event_gainFocus(self, obj, nextHandler)

originalReportLiveRegion = None
@ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_wchar_p, ctypes.c_wchar_p)
def newReportLiveRegion(text: str, politeness: str):
    # We need to figure out current URL, however this can only be done from the main thread.
    # And this callback is not running in the main thread.
    # I haven't found a way to schedule a call to main thread, since core.callLater runs in a different thread.
    # So we use cached value since there is no other good option.
    obj = api.getFocusObject()
    url = None
    try:
        interceptor = obj.treeInterceptor
        if interceptor is not None:
            url = getUrl(interceptor, onlyFromCache=True)
    except AttributeError:
        pass
    if url is not None:
        if DebugBeepMode.ON_LIVE_REGION in getDebugBeepModes(url, globalConfig):
            tones.beep(500, 50)
        if LiveRegionMode.MUTE_LIVE_REGION == getLiveRegionMode(url, globalConfig):
            # Skipping!
            return -1
    return originalReportLiveRegion(text, politeness)

asyncAutoclickCounter = 0
def asyncAutoclick(self, asyncAutoclickCounterLocal, site):
    global asyncAutoclickCounter
    yield site.autoClickOnFocusDelay
    category = site.autoClickCategory
    while True:
        if asyncAutoclickCounter != asyncAutoclickCounterLocal:
            return
        focus = api.getFocusObject()
        try:
            if focus.treeInterceptor != self:
                return
        except AttributeError:
            return
        autoClick(
            self,
            gesture=None,
            category=category,
            site=site,
            automated=True
        )
        if site.autoClickContinuous:
            yield site.autoClickContinuousDelay
        else:
            return

def asyncBrowseMonitor(self):
    """
        This function is just for testing..
        The idea was to spawn multiple async generators one for each browseMode objewct.
        But there can bee too many of them at once. So for now switching to another design: we'll have only a single thread that would only monitor focused browseMode.
    """
    bref = weakref.ref(self)
    del self
    while True:
        yield 1000
        browse = bref()
        try:
            if browse is None:
                tones.beep(2000, 2000)
                return
        finally:
            del browse

class AutoSpeakCacheEntry:
    enabled: bool
    lines = None

    def __init__(self, lines):
        self.lines = lines
        self.enabled = True

browseMonitorThreadShutdownRequested = False
AutoSpeakCache = weakref.WeakKeyDictionary()
def browseMonitorThreadFunc():
    while not browseMonitorThreadShutdownRequested:
        try:
            time.sleep(0.5)
            focus = api.getFocusObject()
            try:
                browse = focus.treeInterceptor
                if browse is None:
                    continue
            except AttributeError:
                continue
            url = getUrl(browse, onlyFromCache=True)
            if url is None:
                continue
            bookmarks = getAutoSpeakBookmarksForUrl(url, globalConfig)
            try:
                cacheEntry = AutoSpeakCache[browse]
            except KeyError:
                cacheEntry = {}
                AutoSpeakCache[browse] = cacheEntry
            processAutoSpeakEntry(browse, bookmarks, cacheEntry)
            try:
                #processWholePageDiff(browse, url)
                pass
            except OSError:
                pass
        except Exception as e:
            #mylog(e)
            #core.callLater(50, ui.message, _("Warning: BrowserNav browse monitor thread crashed: %s") % str(e))
            log.error("Exception in BrowserNav monitor thread", e)

def processAutoSpeakEntry(browse, bookmarks, cacheEntry):
    if len(bookmarks) == 0:
        return
    newLinesByBookmark = _autoClick(browse, gesture=None, category=BookmarkCategory.QUICK_SPEAK, bookmarks=bookmarks,  automated=True)
    for bookmark in bookmarks:
        textToSpeak = newLinesByBookmark.get(bookmark, [])
        try:
            cachedLines = cacheEntry[bookmark]
        except KeyError:
            cachedLines = AutoSpeakCacheEntry([])
            cacheEntry[bookmark] = cachedLines
        processAutoSpeakbookmark(browse, bookmark, textToSpeak, cachedLines)

def processAutoSpeakbookmark(browse, bookmark, textToSpeak, cachedLines):
    if not cachedLines.enabled:
        return
    if False:
        api.c = cachedLines
        api.t = textToSpeak
        mylog(f'asdf {cachedLines.lines == textToSpeak}')
        mylog(f"l={len(cachedLines.lines)}")
        if len(cachedLines.lines)>0:
            mylog(f" 0={cachedLines.lines[0]}")
        mylog(f"l={len(textToSpeak)}")
        if len(textToSpeak) > 0:
            mylog(f" 0={textToSpeak[0]}")

    if False:
        if cachedLines.lines == textToSpeak:
            tones.beep(500, 50)
        else:
            tones.beep(1000, 100)
    firstUtterance = True
    if bookmark.autoSpeakMode == AutoSpeakMode.PARAGRAPH_DIFF:
        for line in diffAndExtractInterestingLines(cachedLines.lines, textToSpeak):
            if line[0] in "!+":
                line = line[1:]
                def speak(firstUtterance):
                    if firstUtterance:
                        speech.cancelSpeech()
                    speech.speakText(line)
                wx.CallAfter(speak, firstUtterance)
    elif bookmark.autoSpeakMode.value.startswith("chime"):
        filterByType = {
            AutoSpeakMode.CHIME_ON_ADD: "+",
            AutoSpeakMode.CHIME_ON_REMOVE: "-",
            AutoSpeakMode.CHIME_ON_CHANGE: "+-!"
        }
        filter = filterByType[bookmark.autoSpeakMode]
        passes = any(line[0] in filter for line in diffAndExtractInterestingLines(cachedLines.lines, textToSpeak))
        if passes:
            playBiw(bookmark)


    cachedLines.lines = textToSpeak

def diffAndExtractInterestingLines(s1, s2):
    if isinstance(s1, str):
        s1 = s1.splitlines()
    if isinstance(s2, str):
        s2 = s2.splitlines()
    mode = '0'
    for line in dl.context_diff(s1, s2):
        if line.startswith('***'):
            mode = 'old'
        elif line.startswith('---'):
            mode = 'new'
        elif mode == 'new' and len(line) > 0 and line[0] in {'!', '+'}:
            yield line
        elif mode == 'old' and len(line) > 0 and line[0] in {'-'}:
            yield line

def playBiw(bookmark=None, earcon=None):
    volume = 100.0
    absPath = os.path.join(
        utils.getSoundsPath(),
        earcon or bookmark.builtInWavFile,
    )
    f = wave.open(absPath,"r")
    if f.getsampwidth() != 2:
        bits = f.getsampwidth() * 8
        raise RuntimeError(f"We only support 16-bit encoded wav files. '{fileName}' is encoded with {bits} bits per sample.")
    buf =  f.readframes(f.getnframes())
    bufSize = len(buf)
    n = bufSize//2
    unpacked = struct.unpack(f"<{n}h", buf)
    unpacked = list(unpacked)
    for i in range(n):
        unpacked[i] = int(unpacked[i] * volume/100)
    packed = struct.pack(f"<{n}h", *unpacked)
    buf = packed
    fileWavePlayer = nvwave.WavePlayer(channels=f.getnchannels(), samplesPerSec=f.getframerate(),bitsPerSample=f.getsampwidth()*8, outputDevice=config.conf["speech"]["outputDevice"],wantDucking=False)
    fileWavePlayer.stop()
    fileWavePlayer.feed(buf)
    fileWavePlayer.idle()


def getTextFast(info):
    fields = info.getTextWithFields()
    text = [s.rstrip("\r\n") for s in fields if isinstance(s, str)]
    return "\r\n".join(text)


wpdCache = weakref.WeakKeyDictionary()
WPDCacheEntry = namedtuple('WPDCacheEntry', ['text'])
def processWholePageDiff(browse, url):
    entry = wpdCache.get(browse, None)
    info = browse.makeTextInfo(textInfos.POSITION_ALL)
    c1 = time.time()
    #newText = info.clipboardText
    newText = getTextFast(info)
    c2 = time.time()
    if entry is not None:
        oldText = entry.text
        linesToSpeak= []
        kinds = {}
        for line in diffAndExtractInterestingLines(oldText, newText):
            if line[0] in "!+":
                linesToSpeak.append(line[1:])
            kind = line[0]
            counter = kinds.get(kind, 0)
            kinds[kind] = counter + 1
        if len(linesToSpeak) > 0:
            if False:
                api.t .append(len(newText))
                api.d.append(len(linesToSpeak))
                api.c.append(c2-c1)
                global debugi
                with open(f"H:\\bn{debugi}.txt", 'w', encoding='utf-8') as f:
                    print(newText, file=f)
                debugi += 1

            def speakLines(lines):
                speech.speakText("\n".join(lines))
            wx.CallAfter(speakLines, linesToSpeak)
        playDiffEarcons(
            add='+' in kinds,
            modify='!' in kinds,
            delete='-' in kinds,
        )
    wpdCache[browse] = WPDCacheEntry(text = newText)

earconDelete = "3d/center.wav"
earconModify = "3d/search-hit.wav"
earconAdd = "3d/search-miss.wav"
def playDiffEarcons(delete, modify, add):
    if add or modify or delete:
        tones.beep(100, 5)
    if False:
        if delete:
            playBiw(earcon=earconDelete)
        if modify:
            playBiw(earcon=earconModify)
        if add:
            playBiw(earcon=earconAdd)


originalBrowseModeReport = None
def preBrowseModeReport(self,readUnit=None):
    url = getUrl(self.document)
    suppress = getSuppressDescription(url, globalConfig)
    originalValue = config.conf["presentation"]["reportObjectDescriptions"]
    if suppress:
        config.conf["presentation"]["reportObjectDescriptions"] = False
    try:
        result = originalBrowseModeReport(self,readUnit)
    finally:
        config.conf["presentation"]["reportObjectDescriptions"] = originalValue
    return result

original_event_treeInterceptor_gainFocus = None
def pre_event_treeInterceptor_gainFocus(self):
    if not self._hadFirstGainFocus:
        #tones.beep(1000, 100)
        #utils.executeAsynchronously(asyncBrowseMonitor(self))
        url = getUrl(self)
        sites = findSites(url, globalConfig)
        autoClickSites = [site for site in sites if site.autoClickOnFocus]
        if len(autoClickSites) >= 2:
            ui.message(_("BrowserNav warning: Two or more sites matching this URL are configured to perform autoClick on load. This is not supported."))
        elif len(autoClickSites) == 1:
            site = autoClickSites[0]
            if site.    autoClickOnFocus:
                global asyncAutoclickCounter
                asyncAutoclickCounter += 1
                utils.executeAsynchronously(asyncAutoclick(self, asyncAutoclickCounter, site))
    return original_event_treeInterceptor_gainFocus(self)

def getKeystrokeFromGesture(gesture):
    #keystroke = gesture.normalizedIdentifiers[-1].split(':')[1]
    keystroke = gesture.identifiers[-1].split(':')[1]
    return keystroke


originalGetAlternativeScript = None
def postGetAlternativeScript(self,gesture,script):
    result = originalGetAlternativeScript(self,gesture,script)
    bookmarkExecuted = False
    keystroke = getKeystrokeFromGesture(gesture)
    url = getUrl(self, onlyFromCache=True)
    if url is None:
        return result
    bookmarks = getBookmarksWithKeystrokesForUrl(url, globalConfig, keystroke)
    mylog(f"{keystroke} >> {url} b={len(bookmarks)}")
    if '8' in keystroke:
        import api
        api.g=gesture
    if "shift+" in keystroke:
        quickJumpKeystroke = keystroke.replace('shift+', '')
        quickJumpDirection = -1
        quickJumpBookmarks = getBookmarksWithKeystrokesForUrl(url, globalConfig, quickJumpKeystroke)
    else:
        quickJumpDirection = 1
        quickJumpBookmarks = bookmarks

    quickJumpBookmarks = tuple(b for b in quickJumpBookmarks if b.category.name.startswith("QUICK_JUMP"))
    quickClikBookmarks = tuple(b for b in bookmarks if b.category.name.startswith("QUICK_CLICK"))
    quickSpeakBookmarks = tuple(b for b in bookmarks if b.category.name.startswith("QUICK_SPEAK"))
    scriptBookmarks = tuple(b for b in bookmarks if b.category.name.startswith("SCRIPT"))

    def keystroke_script(gesture):
        if len(quickJumpBookmarks) > 0:
            _quickJump(self, gesture, quickJumpBookmarks, direction=quickJumpDirection, errorMsg=_("No next QuickJump result. To configure QuickJump rules, please go to BrowserNav settings in NVDA configuration window."))
        if len(quickClikBookmarks) > 0:
            _autoClick(self, gesture, quickClikBookmarks, category=quickClikBookmarks[0].category)
        if len(quickSpeakBookmarks) > 0:
            _autoClick(self, gesture, quickSpeakBookmarks, category=quickSpeakBookmarks[0].category)
        if len(scriptBookmarks) > 0:
            _runScriptBookmarks(self, gesture, scriptBookmarks)
    keystroke_script.__doc__ = _("BrowserNav temporary action configured only for this website.")
    if len(quickJumpBookmarks) + len(quickClikBookmarks) + len(quickSpeakBookmarks) + len(scriptBookmarks) > 0:
        return keystroke_script
    else:
        return result

@functools.lru_cache()
def getRegexForBookmark(rule):
    if rule.patternMatch == PatternMatch.EXACT:
        return f"^{re.escape(rule.pattern)}$"
    elif rule.patternMatch == PatternMatch.SUBSTRING:
        return re.escape(rule.pattern)
    elif rule.patternMatch == PatternMatch.REGEX:
        return rule.pattern
    else:
        raise Exception("Impossible!")

NAMED_REGEX_PREFIX = "QJ_"
BookmarkMatch = namedtuple('BookmarkMatch', ['bookmark', 'text', 'start', 'end'])
@functools.lru_cache()
def makeCompositeRegex(bookmarks):
    # Using named groups in regular expression to identify which bookmark has matched
    re_string = "|".join([
        f"(?P<{NAMED_REGEX_PREFIX}{i}>{getRegexForBookmark(bookmark)})"
        for i,bookmark in enumerate(bookmarks)
    ])
    mylog(f"re_string={re_string}")
    return re_compile(re_string)

def matchWidthCompositeRegex(bookmarks, text):
    m = makeCompositeRegex(bookmarks).search(text)
    if m is None:
        return None
    matchIndices = [
        int(key[len(NAMED_REGEX_PREFIX):])
        for key, value in m.groupdict().items()
        if key.startswith(NAMED_REGEX_PREFIX)
            and value is not None
    ]
    #mylog(f"matchIndices={matchIndices}")
    if len(matchIndices) == 0:
        return
    i = matchIndices[0]

    groupName = f"{NAMED_REGEX_PREFIX}{i}"
    #mylog(f"i={i}")
    #mylog(f"groupName={groupName}")
    return BookmarkMatch(
        bookmark=bookmarks[i],
        text=m.group(groupName),
        start=m.start(groupName),
        end=m.end(groupName),
    )
def matchAllWidthCompositeRegex(bookmarks, text):
    result = []
    while True:
        m = matchWidthCompositeRegex(bookmarks, text)
        if not m:
            return result
        result.append(m)
        bookmarks = tuple([
            b
            for b in bookmarks
            if b != m.bookmark
        ])

def matchTextAndAttributes(bookmarks, textInfo, distance=None):
    text = textInfo.text
    text = text.rstrip("\r\n")
    #mylog(f"matchTextAndAttributes '{text}'")
    matches = matchAllWidthCompositeRegex(bookmarks, text)
    attrs = None
    for m in matches:
        bookmark = m.bookmark
        #mylog(f"bookmark={bookmark.getDisplayName()}")
        #mylog(f"bookmark has {len(bookmark.attributes)} attribute filters.")
        #mylog(f"Bookmark is snippet empty: {bookmark.isSnippetEmpty()}")
        if distance is not None and bookmark.offset * distance < 0:
            # offset is in the opposite direction to current movement direction
            if abs(distance) <= abs(bookmark.offset):
                #mylog("# We don't want to hit the anchor of current bookmark again")
                # We don't want to hit the anchor of current bookmark again
                continue
        if len(bookmark.attributes) > 0:
            if attrs is None:
                attrs = extractAttributesSet(textInfo)
        if all([
            am.matches(attrs)
            for am in bookmark.attributes
        ]):
            #mylog("Yield!")
            yield m
        #mylog("Didn't match attributes")
    #mylog("Done matchTextAndAttributes")

@functools.lru_cache()
def findApplicableBookmarks(
        config=None,
        url=None,
        category=None,
        site=None,
        withoutOffsetOnly=False,
        withDefaultKeystrokeOnly=True
):
    if (url is not None) == (site is not None):
        raise Exception("Must specify either URL or site, but not both.")
    if url is not None:
        sites = findSites(url, config)
    else:
        sites = [site]
    bookmarks = [
        bookmark
        for site in sites
        for bookmark in site.bookmarks
        if (
            bookmark.category == category
            or category is None
        )
        and bookmark.enabled
    ]
    if withoutOffsetOnly:
        bookmarks = [b for b in bookmarks if b.offset == 0 and b.isSnippetEmpty()]
    if withDefaultKeystrokeOnly:
        bookmarks = [b for b in bookmarks if b.keystroke is None]
    return tuple(bookmarks)

@functools.lru_cache()
def findApplicableBookmarksOrderedByOffset(*args, **kwargs):
    bookmarks = findApplicableBookmarks(*args, **kwargs)
    result = {}
    for bookmark in bookmarks:
        l = result.get(bookmark.offset, [])
        l.append(bookmark)
        result[bookmark.offset] = l
    return {k:tuple(v) for k,v in result.items()}
def extractAttributesSet(textInfo):
    result = set()
    fields = textInfo.getTextWithFields()
    for field in fields:
        if not isinstance(field, textInfos.FieldCommand):
            continue
        elif field.command == 'controlStart':
            role = None
            try:
                role = field.field['role']
                result.add(QJAttribute(role=role))
            except KeyError:
                pass
            if role == controlTypes.Role.HEADING:
                try:
                    level = field.field['level']
                    result.add(QJAttribute(heading=level))
                except KeyError:
                    pass
        elif field.command == 'formatChange':
            for key, pAttr in [
                ("level", ParagraphAttribute.HEADING),
                ("font-family", ParagraphAttribute.FONT_FAMILY),
                ("font-size", ParagraphAttribute.FONT_SIZE),
                ("color", ParagraphAttribute.COLOR),
                ("background-color", ParagraphAttribute.BACKGROUND_COLOR),
                ("bold", ParagraphAttribute.BOLD),
                ("italic", ParagraphAttribute.ITALIC),
            ]:
                try:
                    result.add(QJAttribute({
                        'attribute': pAttr,
                        'value': str(field.field[key]).replace(" ", "_"),
                    }))
                except KeyError:
                    pass
        else:
            pass
    return result

def extractAttributes(textInfo):
    result = extractAttributesSet(textInfo)
    return sorted(list(result))

def extractDefaultAttributeMatches(textInfo):
    attrs = extractAttributes(textInfo)
    result = [
        QJAttributeMatch(userString=attr.asString()).asDict()
        for attr in attrs
        if (
            attr.attribute == ParagraphAttribute.ROLE
            and attr.value in {
                ROLE_BUTTON,
                ROLE_HEADING,
                ROLE_LINK,
                ROLE_EDITABLETEXT,
                ROLE_GRAPHIC,
                ROLE_MENUBUTTON,
            }
        ) or (
            attr.attribute == ParagraphAttribute.HEADING
        )
    ]
    return result

def moveParagraph(textInfo, offset):
    result = textInfo.move(textInfos.UNIT_PARAGRAPH, offset)
    textInfo.expand(textInfos.UNIT_PARAGRAPH)
    return result

def shouldSkipClutter(textInfo, allBookmarks):
    if isinstance(allBookmarks, (list, tuple)):
        bookmarks0 = allBookmarks
        bookmarksOther = {}
    else:
        try:
            bookmarks0 = allBookmarks[0]
        except KeyError:
            bookmarksZero = []
        bookmarksOther = allBookmarks
    for match in matchTextAndAttributes(bookmarks0, textInfo):
        scriptMatch, message = runScriptAndApplyOffset(textInfo, match, skipClutterBookmarks=[])
        if scriptMatch is not None:
            return True
    for _offset, bookmarks in bookmarksOther.items():
        offset = -_offset
        if offset == 0:
            continue
        for bookmark in bookmarks:
            if bookmark.bytecode is not None:
                raise QuickJumpScriptException(f"Illegal SkipClutter bookmark '{bookmark.getDisplayName()}' has both non-empty script and non-zero offset.")
        t = textInfo.copy()
        code = moveParagraph(t, offset)
        if code == offset:
            if len(list(matchTextAndAttributes(bookmarks, t))) > 0:
                return True
    return False

def moveParagraphWithSkipClutter(self, textInfo, offset, skipClutterBookmarks=None):
    """
        This function has been disabled.
        Passing skip clutter bookmarks and properly accounting for them
        turns out to be a huge headache.
        Adjusting offsets can now be done via scripting.
    """
    #bookmarks = skipClutterBookmarks or findApplicableBookmarks(globalConfig, getUrl(self), BookmarkCategory.SKIP_CLUTTER, withoutOffsetOnly=True)
    bookmarks = ()
    direction = 1 if offset > 0 else -1
    distance = 0
    while offset != 0:
        code = moveParagraph(textInfo, direction)
        if code == 0:
            return 0
        if shouldSkipClutter(textInfo, bookmarks):
            continue
        distance += 1
        offset -= direction
    return direction * distance

def runScriptAndApplyOffset(textInfo, match, skipClutterBookmarks=None, level=None, modifiers=None):
    """
        This function is called to either apply offset, or evaluate script after we matched a paragraph using primary regex and style.
        Returns tuple
            0-th element represents matched textInfo or None if there was no match.
            1-st element is either string or textInfo to announce prior to match, or None if nothing to announce.
    """
    bookmark = match.bookmark
    textInfo = textInfo.copy()
    mylog(f"q has bytecode {bookmark.bytecode is not None}")
    if bookmark.scriptFunc is None:
        offset = bookmark.offset
        mylog(f"q offset={offset}")
        if offset == 0:
            textInfo.collapse()
            textInfo.move(textInfos.UNIT_CHARACTER, match.start)
            textInfo.move(textInfos.UNIT_CHARACTER, len(match.text), endPoint='end')
            return (textInfo, bookmark.message)
        else:
            mylog("q3")
            result = moveParagraphWithSkipClutter(None, textInfo, offset, skipClutterBookmarks=skipClutterBookmarks)
            mylog(f"q4 {result}")
            if result == offset:
                return (textInfo, bookmark.message)

    else:
        if bookmark.offset != 0:
            e = QuickJumpScriptException(f"Please set offset to 0 for bookmark '{bookmark.getDisplayName()}' in order to execute script.")
            log.error(e)
            raise e
        mylog(f"q compileError present: {bookmark.compileError is not None}")
        if bookmark.compileError is not None:
            e = QuickJumpScriptException(f"Failed to compile snippet for  bookmark '{bookmark.getDisplayName()}'.", bookmark.compileError)
            log.error(e)
            raise e
        p = Paragraph(textInfo)
        t = textInfo.copy()
        _offset = None
        _message = None
        def match(offset=None, message=None):
            nonlocal _offset, _message
            if offset is None:
                offset = 0
            _offset = offset
            _message = message
            raise QuickJumpMatchPerformedException
        execLocals = {
            'p': p,
            't': t,
            'match': match,
            #'allowGeneratorScripts': bookmark.category == BookmarkCategory.SCRIPT,
        }
        #thisExecGlobals = dict(**execGlobals)
        try:
            #exec(bookmark.bytecode, thisExecGlobals, execLocals)
            scriptFunc = bookmark.scriptFunc
            result = scriptFunc(p=p, t=t, match=match, level=level, modifiers=modifiers)
            if isinstance(result, types.GeneratorType):
                allowGeneratorScripts = bookmark.category in [
                    BookmarkCategory.SCRIPT,
                    BookmarkCategory.NUMERIC_SCRIPT,
                ]
                if not allowGeneratorScripts:
                    raise RuntimeError("This script is a generator function; it is only allowed for bookmark type Script and Numeric Script.")
                utils.executeAsynchronously(result)
            elif isinstance(result, tuple):
                match(*result)
            elif isinstance(result, dict):
                match(**result)
            elif result is not None:
                match(result)
        except QuickJumpMatchPerformedException:
            # Script called match function!
            if not (
                _offset is None
                or isinstance(_offset, int)
                or isinstance(_offset, textInfos.TextInfo)
                or isinstance(_offset, Paragraph)
            ):
                e = QuickJumpScriptException(f"First argument of match() function (offset) must be either None, or int, or textInfo, or Paragraph, but got: {type(_offset)}. Please fix your quickJump script for bookmark {bookmark.getDisplayName()}.")
                log.error(e)
                raise e

            if not (
                _message is None
                or isinstance(_message, str)
                or isinstance(_message, textInfos.TextInfo)
                or isinstance(_message, Paragraph)
            ):
                e = QuickJumpScriptException(f"Second argument of match() function (message) must be either None, or string, or textInfo, or Paragraph, but got: {type(_message)}. Please fix your quickJump script for bookmark {bookmark.getDisplayName()}.")
                log.error(e)
                raise e

            if _offset is None:
                _offset = 0
            elif isinstance(_offset, Paragraph):
                _offset = _offset.textInfo
            if isinstance(_message, str) and len(_message) == 0:
                _message = None
            elif isinstance(_message, Paragraph):
                _message = _message.textInfo

            if _message is not None and len(bookmark.message) > 0:
                e = QuickJumpScriptException(f"Second argument of match() function (message) is not empty, while bookmark message is also set. Please either clear bookmark message, or change your script to not return any message. Error in bookmark {bookmark.getDisplayName()}.")
                log.error(e)
                raise e

            message = _message or bookmark.message

            if isinstance(_offset, int):
                result = moveParagraphWithSkipClutter(None, textInfo, _offset, skipClutterBookmarks=skipClutterBookmarks)
                if result == _offset:
                    return (textInfo, message)
            else:
                return (_offset, message)
        except ScriptError as e:
            message = str(e)
            log.error("ScriptError: {}", e)
            ui.message(message)
        #except Exception as e:
        #    e2 = QuickJumpScriptException(f"Exception while running script for bookmark '{bookmark.getDisplayName()}'.", e)
        #    log.error(e2)
        #    raise e
    return (None, None)

def matchAndScript(bookmarks, skipClutterBookmarks, textInfo):
    #mylog("matchAndScript start")
    for match in matchTextAndAttributes(bookmarks, textInfo):
        #mylog("q1")
        result, message = runScriptAndApplyOffset(textInfo, match, skipClutterBookmarks)
        #mylog("q2")
        if result  is not None:
            #mylog("matchAndScript Result is not None :(")
            return result, message, match
    #mylog("matchAndScript Result is  None :(")
    return None, None, None

def isMatchInRightDirection(oldSelection, direction, textInfo):
    origin = oldSelection.copy()
    origin.collapse(end=direction>0)
    origin.expand(textInfos.UNIT_PARAGRAPH)
    origin.collapse(end=direction>0)
    if direction > 0:
        origin.move(textInfos.UNIT_CHARACTER, -1)
    cmp = origin.compareEndPoints(textInfo, "startToStart")
    return direction * cmp < 0

def getBookmarksForCategory(self, category):
    url = getUrl(self)
    bookmarks = findApplicableBookmarks(globalConfig, url, category)
    return bookmarks

def quickJump(self, gesture, category, direction, errorMsg):
    bookmarks = getBookmarksForCategory(self, category)
    return _quickJump(self, gesture, bookmarks, direction, errorMsg)

def _quickJump(self, gesture, bookmarks, direction, errorMsg):
    oldSelection = self.selection
    if len(bookmarks) == 0:
        return endOfDocument(_('No quickJump bookmarks configured for current website. Please add QuickJump bookmarks in BrowserNav settings in NVDA settings window.'))
    textInfo = self.makeTextInfo(textInfos.POSITION_CARET)
    textInfo.collapse()
    textInfo.expand(textInfos.UNIT_PARAGRAPH)
    originalParagraph = textInfo.copy()
    distance = 0
    adjustedDistance = 0
    while True:
        result = moveParagraph(textInfo, direction)
        if result == 0:
            endOfDocument(errorMsg)
            return
        distance += 1
        adjustedDistance += 1

        matchInfo, message, dummyMatch = matchAndScript(bookmarks, [], textInfo)
        if matchInfo is not None:
            if not isMatchInRightDirection(oldSelection, direction, matchInfo):
                continue
            textInfo = matchInfo
            utils.speakMessage(message)
            textInfo.updateCaret()
            speech.speakTextInfo(textInfo, reason=REASON_CARET)
            textInfo.collapse()
            self._set_selection(textInfo)
            self.selection = textInfo
            sonifyTextInfo(self.selection, oldTextInfo=oldSelection, includeCrackle=True)
            return

def caretMovementWithAutoSkip(self, gesture,unit, direction=None,posConstant=textInfos.POSITION_SELECTION, *args, **kwargs):
    bookmarks = findApplicableBookmarksOrderedByOffset(globalConfig, getUrl(self), BookmarkCategory.SKIP_CLUTTER)
    skipped = False
    oldInfo=self.makeTextInfo(posConstant)
    info=oldInfo.copy()
    info.collapse(end=self.isTextSelectionAnchoredAtStart)
    if self.isTextSelectionAnchoredAtStart and not oldInfo.isCollapsed:
        info.move(textInfos.UNIT_CHARACTER,-1)
    info.expand(unit)
    text = info.text
    info.collapse()
    for i in range(100):
        result = info.move(unit,direction)
        if result == 0:
            break
        expandInfo = info.copy()
        expandInfo.expand(unit)
        expandText = expandInfo.text
        if shouldSkipClutter(expandInfo, bookmarks):
            skipped = True
            continue
        break
    selection = info.copy()
    info.expand(unit)
    speech.speakTextInfo(info, unit=unit, reason=REASON_CARET)
    if not oldInfo.isCollapsed:
        speech.speakSelectionChange(oldInfo, selection)
    self.selection = selection
    if skipped:
        skippedParagraphChime()


def autoClick(self, gesture, category, site=None, automated=False):
    if site is None:
        bookmarks = findApplicableBookmarks(globalConfig, getUrl(self), category)
    else:
        bookmarks = findApplicableBookmarks(category=category, site=site)
    mylog(f"asdf {category}")
    return _autoClick(self, gesture, bookmarks, site, automated, category=category)

AutoSpeakTextCache = weakref.WeakKeyDictionary()
def _autoClick(self, gesture, bookmarks, site=None, automated=False, category=None):
    """
        This function handles both quick_click and quick_speak bookmarks.
    """
    isSpeak = category == BookmarkCategory.QUICK_SPEAK
    isClick = category.name.startswith("QUICK_CLICK")
    if isSpeak == isClick:
        raise RuntimeError(f"Invalid category {category.name}")


    mylog(f"Autoclick Found {len(bookmarks)} bookmarks")
    if len(bookmarks) == 0:
        return endOfDocument(
            _('No {category} bookmarks configured for current website. Please add {category} bookmarks in BrowserNav settings in NVDA settings window.').format(
                category=BookmarkCategoryShortNames[category],
            )
        )
    textInfo = self.makeTextInfo(textInfos.POSITION_ALL)
    textInfo.collapse()
    textInfo.expand(textInfos.UNIT_PARAGRAPH)
    distance = 0
    message = None
    focusableErrorMsg = None
    focusables = []
    textToSpeak = []
    textToSpeakByBookmark = {}
    while True:
        matchInfo, thisMessage, match = matchAndScript(bookmarks, skipClutterBookmarks=[], textInfo=textInfo)
        if matchInfo is not None:
            thisInfo = matchInfo
            if isClick:
                mylog(f"Autoclick Match {distance} {thisInfo.text}")
                focusable = thisInfo.focusableNVDAObjectAtStart
                if focusable.role in {ROLE_DOCUMENT, ROLE_DIALOG}:
                    if focusableErrorMsg is None:
                        mylog("Bookmark points to non-focusable NVDA object, cannot click it.")
                        focusableErrorMsg = _("Bookmark points to non-focusable NVDA object, cannot click it.")
                else:
                    mylog("Verification skipped since offset is non-zero")
                    focusables.append(focusable)
                    if message is None and thisMessage  is not None and len(thisMessage) > 0:
                        message = thisMessage
            elif isSpeak:
                entries = []
                if thisMessage is not None and len(thisMessage) > 0:
                    entries.append(thisMessage)
                entries.append(thisInfo.text)
                textToSpeak.extend(entries)
                try:
                    ttsb = textToSpeakByBookmark[match.bookmark]
                except KeyError:
                    ttsb = []
                    textToSpeakByBookmark[match.bookmark] = ttsb
                ttsb.extend(entries)

            else:
                error_hahaha
        distance += 1
        result = moveParagraph(textInfo, 1)
        if result == 0:
            break
    if isClick:
        numSuccessfulClicks = 0
        for focusable in focusables:
            try:
                focusable.doAction()
                numSuccessfulClicks += 1
            except NotImplementedError as e:
                # Not sure why this is occasionally thrown
                pass
        if numSuccessfulClicks == 0:
            if not automated:
                endOfDocument(focusableErrorMsg or _("No bookmarks matched!"))
            return
        if automated:
            if site is not None and site.debugBeepMode == DebugBeepMode.ON_AUTO_CLICK:
                tones.beep(500, 50)
        else:
            if message is not None:
                ui.message(message)
            else:
                ui.message(_("Clicked {n} objects.").format(
                    n=len(focusables)
                ))
    elif isSpeak:
        if automated:
            return textToSpeakByBookmark
        mylog(f"  tts1 = {textToSpeak}")
        textToSpeak = [s for s in textToSpeak if s is not None and len(s) > 0]
        if len(textToSpeak) > 0:
            mylog(f"  tts2 = {textToSpeak}")
            textToSpeak = "\n".join(textToSpeak)
            mylog(f"  calling speak {textToSpeak}")
            #tones.beep(500, 50)
            def speak():
                speech.cancelSpeech()
                speech.speakText(textToSpeak)
            #core.callLater(0, speak)
            wx.CallAfter(speak)
    else:
        error


class HierarchicalLevelsInfo:
    offsets: List[int]
    def __init__(self, offsets):
        self.offsets = offsets

hierarchicalCache = weakref.WeakKeyDictionary()
def getIndentFunc(textInfo, documentHolder, future):
    try:
        x = utils.getGeckoParagraphIndent(textInfo, documentHolder)
        future.set(x)
    except Exception as e:
        future.setException(e)

def scanLevelsThreadFunc(self, config, future, bookmarks):
    #mylog("sltf begin")
    futures = []
    direction = 1
    try:
        category = BookmarkCategory.HIERARCHICAL
        mylog(f"sltf bookmarks={len(bookmarks)} url=?")
        if len(bookmarks) == 0:
            future.set([])
            return
        textInfo = self.makeTextInfo(textInfos.POSITION_ALL)
        textInfo.collapse()
        textInfo.expand(textInfos.UNIT_PARAGRAPH)
        document = utils.getIA2Document(textInfo)
        documentHolder = utils.DocumentHolder(document)
        distance = 0
        #mylog(f"loop:sltf->matchTextAndAttributes({len(bookmarks)})")
        while True:
            matchInfo, message, dummyMatch = matchAndScript(bookmarks, skipClutterBookmarks=[], textInfo=textInfo)
            if matchInfo is not None:
                # We compute x screen coordinate of the match
                # Computing it in thread pool for performance reasons.
                innerFuture = utils.Future()
                utils.threadPool.add_task(getIndentFunc, matchInfo, documentHolder, innerFuture)
                futures.append(innerFuture)

            distance += 1
            result = moveParagraph(textInfo, direction)
            if result == 0:
                # collect all the futures and return
                result = HierarchicalLevelsInfo(sorted(list({
                    inner.get()
                    for inner in futures
                })))
                future.set(result)
                #mylog("sltf success")
                #mylog(f"sltf result={result.offsets}")
                return
    except Exception as e:
        #mylog("sltf fail")
        future.setException(e)


def scanLevels(self, bookmarks):
    global globalConfig, hierarchicalCache
    config = globalConfig
    future = utils.Future()
    utils.threadPool.add_task(scanLevelsThreadFunc, self, config, future, bookmarks)
    try:
        innerDict = hierarchicalCache[self]
    except KeyError:
        innerDict = {}
        hierarchicalCache[self] = innerDict
    innerDict[config] = future
    return future

def hierarchicalQuickJump(self, gesture, category, direction, level, unbounded, errorMsg):
    url = getUrl(self)
    hierarchicalBookmarks = findApplicableBookmarks(globalConfig, url, BookmarkCategory.HIERARCHICAL)
    numericScriptBookmarks = findApplicableBookmarks(globalConfig, url, BookmarkCategory.NUMERIC_SCRIPT)
    if len(hierarchicalBookmarks) > 0:
        if len(numericScriptBookmarks) > 0:
            ui.message(_("Both hierarchical and numeric script bookmarks are configured for this website. This is not supported; please disable either hierarchical or numeric script bookmarks."))
        else:
            return _hierarchicalQuickJump(self, gesture, category, direction, level, unbounded, errorMsg)
    else:
        if len(numericScriptBookmarks) > 0:
            return _numericScriptKeystroke(self, gesture, direction, level, numericScriptBookmarks)
        else:
            return endOfDocument(_('No hierarchical quickJump bookmarks or numeric script bookmarks configured for current website. Please add QuickJump bookmarks in BrowserNav settings in NVDA settings window.'))

def _hierarchicalQuickJump(self, gesture, category, direction, level, unbounded, errorMsg):
    oldSelection = self.selection
    url = getUrl(self)
    bookmarks = findApplicableBookmarks(globalConfig, url, category)
    mylog(f"hqj bookmarks={len(bookmarks)} url={url}")
    skipClutterBookmarks = findApplicableBookmarks(globalConfig, url, BookmarkCategory.SKIP_CLUTTER)
    if len(bookmarks) == 0:
        return endOfDocument(_('No hierarchical quickJump bookmarks configured for current website. Please add QuickJump bookmarks in BrowserNav settings in NVDA settings window.'))
    try:
        levelsInfo = hierarchicalCache[self][globalConfig].get()
    except KeyError:
        levelsInfo = None
        scanLevels(self, bookmarks)
        mylog(f"levelsInfo is None")
        levelsInfo = hierarchicalCache[self][globalConfig].get()
    mylog(f"level={level} levelsInfo={levelsInfo.offsets}")
    textInfo = self.makeTextInfo(textInfos.POSITION_CARET)
    textInfo.collapse()
    textInfo.expand(textInfos.UNIT_PARAGRAPH)
    document = utils.getIA2Document(textInfo)
    documentHolder = utils.DocumentHolder(document)
    distance = 0
    adjustedDistance = 0
    mylog(f"hqj->loop:matchTextAndAttributes(skipClutter:{len(skipClutterBookmarks)}")
    mylog(f"hqj->loop:matchTextAndAttributes({len(bookmarks)}")
    while True:
        result = moveParagraph(textInfo, direction)
        if result == 0:
            #mylog("end of document")
            endOfDocument(errorMsg)
            return
        distance += 1
        adjustedDistance += 1
        #mylog("hqj->matchTextAndAttributes2")
        mylog("HQJ calling matchAndScript")
        mylog(f"asdf {textInfo.text}")
        matchInfo, message, dummyMatch = matchAndScript(bookmarks, [], textInfo)
        mylog(f"asdf2 {textInfo.text}")
        if matchInfo is not None:
            if not isMatchInRightDirection(oldSelection, direction, matchInfo):
                continue
            thisInfo = matchInfo
            offset = utils.getGeckoParagraphIndent(thisInfo, documentHolder)
            mylog(f"thisInfo={thisInfo.text}")
            mylog(f"offset={offset}")
            if (
                levelsInfo is None
                or level is None
                or (
                    offset in levelsInfo.offsets
                    and levelsInfo.offsets.index(offset) == level
                )
            ):
                mylog("Perfect")
                if (
                    level is None
                    and levelsInfo is not None
                    and offset in levelsInfo.offsets
                ):
                    announceLevel = levelsInfo.offsets.index(offset) + 1
                    ui.message(_("Level {announceLevel}").format(announceLevel=announceLevel))
                if message is not None and len(message) > 0:
                    ui.message(message)
                thisInfo.updateCaret()
                speech.speakTextInfo(thisInfo, reason=REASON_CARET)
                thisInfo.collapse()
                self._set_selection(thisInfo)
                self.selection = thisInfo
                sonifyTextInfo(self.selection, oldTextInfo=oldSelection, includeCrackle=True)
                return
            elif offset not in levelsInfo.offsets:
                # Something must have happened that current level is not recorded in the previous scan. Rescan after this script.
                mylog("offset not in levelsInfo")
                scanLevels(self, bookmarks)
                endOfDocument(_("BrowserNav error: inconsistent indents in the document. Recomputing indents, please try again."))
                return
            elif levelsInfo.offsets.index(offset) > level:
                #mylog("levelsInfo.offsets.index(offset) > level")
                continue
            elif levelsInfo.offsets.index(offset) < level:
                #mylog("levelsInfo.offsets.index(offset) < level")
                if unbounded:
                    continue
                else:
                    endOfDocument(errorMsg)
                    return
            else:
                raise Exception("Impossible!")


numericScriptNumberEntryInProgress = False
numericScriptEntries = []
numericScriptNegativeMultiplier = 1
numericScriptModifiers = None
def awaitNumberForNumericScript(self, bookmarks):
    global numericScriptNumberEntryInProgress
    if numericScriptNumberEntryInProgress:
        raise RuntimeError("numericScriptNumberEntryInProgress is True")
    numericScriptNumberEntryInProgress = True
    try:
        yield from utils.waitForModifiersToBeReleased(60)
    finally:
        numericScriptNumberEntryInProgress = False
    _runScriptBookmarks(self, None, bookmarks, isNumeric=True)

def _numericScriptKeystroke(self, gesture, direction, level, bookmarks):
    global numericScriptEntries, numericScriptModifiers, numericScriptNegativeMultiplier

    if numericScriptNumberEntryInProgress:
        numericScriptEntries.append(level)
        return
    else:
        numericScriptEntries = [level]
        numericScriptModifiers = utils.getCurrentModifiers()
        numericScriptNegativeMultiplier = -1 if "shift" in gesture.modifierNames else 1
        utils.executeAsynchronously(awaitNumberForNumericScript(self, bookmarks))



def _runScriptBookmarks(self, gesture, bookmarks, isNumeric=False):
    level = None
    modifiers = None
    if isNumeric:
        modifiers = numericScriptModifiers
        levels = numericScriptEntries
        if None in levels:
            if len(levels) > 1:
                ui.message(_("Cannot combine tilde with digits for numeric script!"))
                return
            level = None
        else:
            levels = [str((i+1)%10) for i in levels]
            try:
                level = int("".join(levels)) * numericScriptNegativeMultiplier
            except ValueError:
                ui.message(
                    _("Invalid level for numeric script: '{level}'")
                    .format(level = "".join(levels))
                )
                return
    for bookmark in bookmarks:
        textInfo = self.selection
        match = BookmarkMatch(
            bookmark=bookmark,
            text=None,
            start=0,
            end=0,
        )
        runScriptAndApplyOffset(textInfo, match, level=level, modifiers=modifiers)

def editOrCreateSite(self, site=None, url=None, domain=None):
    global globalConfig
    config = globalConfig
    try:
        index = config.sites.index(site)
        knownSites = config.sites[:index] + globalConfig.sites[index+1:]
    except ValueError:
        index = None
        knownSites = config.sites
    entryDialog=EditSiteDialog(None, knownSites=knownSites, site=site, url=url, domain=domain, config=config)
    if entryDialog.ShowModal()==wx.ID_OK:
        sites = list(config.sites)
        mylog(f"len(sites) = {len(sites)} index={index}")
        if index is not None:
            sites[index] = entryDialog.site
        else:
            sites.append(entryDialog.site)
        mylog(f"Afterwards len(sites) = {len(sites)} new name = {entryDialog.site.getDisplayName()}")
        config = config.updateSites(sites)
        globalConfig = config
        saveConfig()
        mylog(f"Config saved!")
def makeWebsiteSubmenu(self, frame):
    url = getUrl(self)
    sites = findSites(url, globalConfig)
    menu = wx.Menu()

    for site in sites:
        menuStr = _("Edit existing website %s") % site.getDisplayName()
        item = menu.Append(wx.ID_ANY, menuStr)
        frame.Bind(
            wx.EVT_MENU,
            lambda evt, site=site: editOrCreateSite(self, site=site),
            item,
        )

    try:
        domain = getDomain(url)
        menuStr = _("Create new website for domain %s") % domain
        item = menu.Append(wx.ID_ANY, menuStr)
        frame.Bind(
            wx.EVT_MENU,
            lambda evt: editOrCreateSite(self, domain=domain),
            item,
        )
    except ValueError:
        pass
    menuStr = _("Create new website with custom URL matching options")
    item = menu.Append(wx.ID_ANY, menuStr)
    frame.Bind(
        wx.EVT_MENU,
        lambda evt: editOrCreateSite(self, url=url),
        item,
    )
    return menu

def editOrCreateBookmark(self, site, bookmark=None, paragraphInfo=None, text=None):
    global globalConfig
    config = globalConfig
    siteIndex = config.sites.index(site)
    if bookmark is not None:
        bookmarkIndex = site.bookmarks.index(bookmark)
    else:
        bookmarkIndex = None
    entryDialog=EditBookmarkDialog(
        parent=None,
        bookmark=bookmark,
        config=config,
        site=site,
        paragraphInfo=paragraphInfo,
        allowSiteSelection=(bookmark is not None),
        text=text,
    )
    if entryDialog.ShowModal()==wx.ID_OK:
        if site != entryDialog.newSite:
            # moving to newSite!
            # Step 1: updating destination site by adding bookmark there
            newSite = entryDialog.newSite
            bookmarks = list(newSite.bookmarks)
            bookmarks.append(entryDialog.bookmark)
            newSite2 = newSite.updateBookmarks(bookmarks)
            sites = list(config.sites)
            index = sites.index(newSite)
            sites[index] = newSite2
            # Step 2: Removing bookmark from old site:
            bookmarks = list(sites[siteIndex].bookmarks)
            del bookmarks[bookmarkIndex]
            sites[siteIndex] = sites[siteIndex].updateBookmarks(bookmarks)

            config = config.updateSites(sites)
        else:
            # Adding or updating bookmark
            sites = list(config.sites)
            bookmarks = list(sites[siteIndex].bookmarks)
            if bookmarkIndex is not None:
                bookmarks[bookmarkIndex] = entryDialog.bookmark
            else:
                bookmarks.append(entryDialog.bookmark)
            sites[siteIndex] = sites[siteIndex].updateBookmarks(bookmarks)

            config = config.updateSites(sites)
        globalConfig = config
        saveConfig()

def makeBookmarkSubmenu(self, frame):
    menu = wx.Menu()
    textInfo = self.selection.copy()
    paragraphInfo = textInfo.copy()
    paragraphInfo.collapse()
    paragraphInfo.expand(textInfos.UNIT_PARAGRAPH)
    if textInfo.isCollapsed:
        withinParagraph = True
        text = paragraphInfo.text
    else:
        text = textInfo.text
        beginInfo = textInfo.copy()
        beginInfo.collapse()
        beginInfo.expand(textInfos.UNIT_PARAGRAPH)
        endInfo = textInfo.copy()
        endInfo.collapse(end=True)
        endInfo.move(textInfos.UNIT_CHARACTER, -1)
        endInfo.expand(textInfos.UNIT_PARAGRAPH)
        withinParagraph = beginInfo == endInfo
    if not withinParagraph:
        menuStr = _("Current selection spans across multiple paragraphs.")
        errorMsg = menuStr + "\n" + _("Bookmarks that span across paragraphs is not supported by BrowserNav. Please clear the selection or select something within a single paragraph.")
        item = menu.Append(wx.ID_ANY, menuStr)
        frame.Bind(
            wx.EVT_MENU,
            lambda evt: gui.messageBox(errorMsg, _("Bookmark Error"), wx.OK|wx.ICON_WARNING, frame),
            item,
        )
        return menu
    url = getUrl(self)
    sites = findSites(url, globalConfig)
    if len(sites) == 0:
        menuStr = _("No sites are configured for current URL.")
        errorMsg = menuStr + "\n" + _("Please create a new site configuration in site submenu.")
        item = menu.Append(wx.ID_ANY, menuStr)
        frame.Bind(
            wx.EVT_MENU,
            lambda evt: gui.messageBox(errorMsg, _("Bookmark Error"), wx.OK|wx.ICON_WARNING, frame),
            item,
        )
        return menu

    bookmarks = findApplicableBookmarks(globalConfig, url, category=None, withDefaultKeystrokeOnly=False)
    matches = matchAllWidthCompositeRegex(bookmarks, text)
    attributes = extractAttributes(paragraphInfo)

    for m in matches:
        bookmark = m.bookmark
        site_ = [
            site
            for site in sites
            if bookmark in site.bookmarks
        ]
        if len(site_) != 1:
            raise Exception("Impossible!")
        site = site_[0]
        attributesMatch = all([
            am.matches(attributes)
            for am in bookmark.attributes
        ])
        if attributesMatch:
            menuStr = _("Edit perfect match bookmark {bookmark} of category {category} from site {site}")
        else:
            menuStr = _("Edit bookmark {bookmark} of category {category} that doesn't match formatting for current paragraph from site {site}")
        menuStr = menuStr.format(
            bookmark=bookmark.getDisplayName(),
            category=BookmarkCategoryShortNames[bookmark.category],
            site=site.getDisplayName()
        )
        item = menu.Append(wx.ID_ANY, menuStr)
        frame.Bind(
            wx.EVT_MENU,
            lambda evt, site=site, bookmark=bookmark: editOrCreateBookmark(self, site, bookmark, paragraphInfo),
            item,
        )
    for site in sites:
        menuStr = _("Create new bookmark from current paragraph for site {site}").format(
            site=site.getDisplayName()
        )
        item = menu.Append(wx.ID_ANY, menuStr)
        frame.Bind(
            wx.EVT_MENU,
            lambda evt, site=site: editOrCreateBookmark(self, site, paragraphInfo=paragraphInfo, text=text),
            item,
        )
    return menu

def getBrowseModeDefaultKeystrokeByFunc(funcName):
    bmGestures = browseMode.BrowseModeTreeInterceptor._BrowseModeTreeInterceptor__gestures
    results = [
        k
        for k, v in bmGestures.items()
        if v == funcName
    ]
    if len(results) > 0:
        result = results[0]
        prefix = "kb:"
        if result.startswith(prefix):
            result = result[len(prefix):]
        return result
    else:
        return "N/A"
    quickJumpForward
def getDefaultKeystroke(category):
    categoriesToFuncNames = {
        BookmarkCategory.QUICK_JUMP: "quickJumpForward",
        BookmarkCategory.QUICK_JUMP_2: "quickJump2Forward",
        BookmarkCategory.QUICK_JUMP_3: "quickJump3Forward",
        BookmarkCategory.QUICK_CLICK: "autoClick",
        BookmarkCategory.QUICK_CLICK_2: "autoClick2",
        BookmarkCategory.QUICK_CLICK_3:  "autoClick3",
        BookmarkCategory.QUICK_SPEAK: "quickSpeak",
    }
    try:
        funcName = categoriesToFuncNames[category]
    except KeyError:
        if category == BookmarkCategory.HIERARCHICAL:
            return "Alt+1 .. Alt+9"
        elif category == BookmarkCategory.NUMERIC_SCRIPT:
            return "Alt+0 .. Alt+9"
        else:
            return "N/A"
    return getBrowseModeDefaultKeystrokeByFunc(funcName)


class EditBookmarkDialog(wx.Dialog):
    def __init__(self, parent, bookmark=None, config=None, site=None, allowSiteSelection=False, paragraphInfo=None, text=None):
        title=_("Edit browserNav bookmark")
        super(EditBookmarkDialog,self).__init__(parent,title=title)
        self.config=config
        self.oldSite = site
        self.allowSiteSelection = allowSiteSelection
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        if bookmark is  not None:
            self.bookmark = bookmark
        else:
            self.bookmark = QJBookmark({
                'enabled': True,
                'category': BookmarkCategory.QUICK_JUMP,
                'name': "",
                'pattern': text if text is not None else "",
                'patternMatch':
                    PatternMatch.EXACT if (
                        paragraphInfo is not None
                        and text is not None
                        and text == paragraphInfo.text
                    ) else PatternMatch.SUBSTRING,
                'attributes': extractDefaultAttributeMatches(paragraphInfo) if paragraphInfo is not None else [],
                'message': "",
                'offset': 0,
            })
        self.snippet = self.bookmark.snippet
        self.cursorLine, self.cursorColumn = 0,0
        self.keystroke = self.bookmark.keystroke
      # Translators: pattern
        patternLabelText = _("&Pattern")
        self.patternTextCtrl=sHelper.addLabeledControl(patternLabelText, wx.TextCtrl)
        self.patternTextCtrl.SetValue(self.bookmark.pattern)

      # Translators: Pattern match type comboBox
        matchModeLabelText=_("Pattern &match type:")
        self.matchModeCategory=guiHelper.LabeledControlHelper(
            self,
            matchModeLabelText,
            wx.Choice,
            choices=[
                patterMatchNames[m]
                for m in PatternMatch
            ],
        )
        self.matchModeCategory.control.SetSelection(list(PatternMatch).index(self.bookmark.patternMatch))
      # Translators:  Category combo box
        categoryText = _("&Category:")
        self.categoryComboBox = guiHelper.LabeledControlHelper(
            self,
            categoryText,
            wx.Choice,
            choices=[BookmarkCategoryNames[i] for i in BookmarkCategory],
        )
        self.categoryComboBox.control.Bind(wx.EVT_CHOICE,self.onCategory)
        self.categoryComboBox.control.SetSelection(list(BookmarkCategory).index(self.bookmark.category))
      # Translators:  Custom keystroke button
        self.customeKeystrokeButton = sHelper.addItem (wx.Button (self, label = _("Custom &Keystroke")))
        self.customeKeystrokeButton.Bind(wx.EVT_BUTTON, self.OnCustomKeystrokeClick)
        self.updateCustomKeystrokeButtonLabel()
      # Translators: site  comboBox
        labelText=_("&Site this bookmark belongs to:")
        self.siteComboBox=guiHelper.LabeledControlHelper(
            self,
            labelText,
            wx.Choice,
            choices=[
                site.getDisplayName()
                for site in self.config.sites
            ] if allowSiteSelection else [],
        )
        if allowSiteSelection:
            self.siteComboBox.control.SetSelection(
                self.config.sites.index(self.oldSite)
            )
        else:
            self.siteComboBox.control.Disable()
      # Translators: label for enabled checkbox
        enabledText = _("Bookmark enabled")
        self.enabledCheckBox=sHelper.addItem(wx.CheckBox(self,label=enabledText))
        self.enabledCheckBox.SetValue(self.bookmark.enabled)

      # Translators: label for comment edit box
        commentLabelText = _("&Display name (optional)")
        self.commentTextCtrl=sHelper.addLabeledControl(commentLabelText, wx.TextCtrl)
        self.commentTextCtrl.SetValue(self.bookmark.name)
      # Translators: label for Message edit box
        labelText = _("Spoken &message when bookmark is found:")
        self.messageTextCtrl=sHelper.addLabeledControl(labelText, wx.TextCtrl)
        self.messageTextCtrl.SetValue(self.bookmark.message)
      # offset spin
        labelText = _("Offset in paragraphs - select a value to place the cursor on following or preceding paragraph from the bookmark match:")
        self.offsetEdit = sHelper.addLabeledControl(
            labelText, nvdaControls.SelectOnFocusSpinCtrl,
            min=-100, max=100,
            initial=self.bookmark.offset
        )
      # attributes
        labelText = _("&Attributes (space separated list):")
        self.attributesTextCtrl=sHelper.addLabeledControl(labelText, wx.TextCtrl)
        self.attributesTextCtrl.SetValue(" ".join([
            attr.asString()
            for attr in self.bookmark.attributes
        ]))

      # available attributes in current paragraph
        labelText=_("Available attributes in current paragraph (press space to add to current bookmark):")
        self.attrChoices = [
            attr.asString()
            for attr in extractAttributes(paragraphInfo)
        ] if paragraphInfo is not None else []
        self.availableAttributesListBox=guiHelper.LabeledControlHelper(
            self,
            labelText,
            wx.ListBox,
            choices=self.attrChoices,
        )
        #self.availableAttributesListBox.control.Bind(wx.EVT_LISTBOX, self.onAvailableAttributeListChoice)
        self.availableAttributesListBox.control.Bind(wx.EVT_CHAR, self.onChar)
        if paragraphInfo is None:
            self.availableAttributesListBox.control.Disable()
      # enable Autospeak checkbox
        if False:
            labelText = _("Automatically detect and speak changes to this bookmark")
            self.autoSpeakEnabledCheckBox=sHelper.addItem(wx.CheckBox(self,label=labelText))
            self.autoSpeakEnabledCheckBox.SetValue(self.bookmark.enableAutoSpeak)
      # Translators:  AutospeakMode comboBox
        labelText = _("AutoSpeak mode")
        self.autoSpeakModeComboBox = guiHelper.LabeledControlHelper(
            self,
            labelText,
            wx.Choice,
            choices=[autoSpeakModeNames[i] for i in AutoSpeakMode],
        )
        self.autoSpeakModeComboBox.control.Bind(wx.EVT_CHOICE,self.onAutoSpeakMode)
        self.autoSpeakModeComboBox.control.SetSelection(list(AutoSpeakMode).index(self.bookmark.autoSpeakMode))
      # Translators: built in wav category  combo box
        biwCategoryLabelText=_("Chime &category:")
        self.biwCategory=guiHelper.LabeledControlHelper(
            self,
            biwCategoryLabelText,
            wx.Choice,
            choices=self.getBiwCategories(),
        )
        self.biwCategory.control.Bind(wx.EVT_CHOICE,self.onBiwCategory)

      # Translators: built in wav file combo box
        biwListLabelText=_("C&hime:")
        self.biwList=guiHelper.LabeledControlHelper(
            self,
            biwListLabelText,
            wx.Choice,
            choices=[],
        )
        self.biwList.control.Bind(wx.EVT_CHOICE,self.onBiw)
        self.setBiw(self.bookmark.builtInWavFile)
      # Edit script button
        self.editScriptButton = sHelper.addItem (wx.Button (self, label = _("Edit &script in new window; press Control+Enter when Done.")))
        self.editScriptButton.Bind(wx.EVT_BUTTON, self.OnEditScriptClick)


      #  OK/cancel buttons
        sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))

        mainSizer.Add(sHelper.sizer,border=20,flag=wx.ALL)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        self.patternTextCtrl.SetFocus()
        self.Bind(wx.EVT_BUTTON,self.onOk,id=wx.ID_OK)

        self.onCategory(None)
        self.onAutoSpeakMode(None)

    def make(self, snippet=None, quiet=False):
        patternMatch = list(PatternMatch)[self.matchModeCategory.control.GetSelection()]
        pattern = self.patternTextCtrl.Value
        pattern = pattern.rstrip("\r\n")
        errorMsg = None
        if (
            len(pattern) == 0
            and  self.getCategory() not in {
                BookmarkCategory.SCRIPT,
                BookmarkCategory.NUMERIC_SCRIPT,
            }
        ):
            errorMsg = _('Pattern cannot be empty!')
        elif patternMatch == PatternMatch.REGEX:
            try:
                re.compile(pattern)
            except re.error as e:
                errorMsg = _('Failed to compile regular expression: %s') % str(e)

        if errorMsg is not None:
            # Translators: This is an error message to let the user know that the pattern field is not valid.
            gui.messageBox(errorMsg, _("Bookmark entry error"), wx.OK|wx.ICON_WARNING, self)
            self.patternTextCtrl.SetFocus()
            return
        try:
            attributes = [
                QJAttributeMatch(userString=attr)
                for attr in self.attributesTextCtrl.GetValue().strip().split()
            ]
        except ValueError as e:
            errorMsg = _(f'Cannot parse attribute: {e}')
            gui.messageBox(errorMsg, _("Bookmark Entry Error"), wx.OK|wx.ICON_WARNING, self)
            self.attributesTextCtrl.SetFocus()
            return
        if  self.getCategory() == BookmarkCategory.SKIP_CLUTTER and not quiet:
            result = gui.messageBox(
                _("Warning: you are about to create or update a skip clutter bookmark. If your pattern is too generic, it might hide significant part of your website. For example, if you specify a single whitespace as pattern and substring match, then all paragraphs containing at least a single whitespace would disappear. Please make sure you understand how skip clutter works and how to undo this change if you have to. Would you like to continue?"),
                _("Bookmark Entry warning"),
                wx.YES|wx.NO|wx.ICON_WARNING,
                self
            )
            if result == wx.YES:
                pass
            else:
                self.categoryComboBox.control.SetFocus()
                return None

        bookmark = QJBookmark({
            'enabled': self.enabledCheckBox.Value,
            'category': self.getCategory(),
            'name':self.commentTextCtrl.Value,
            'pattern': pattern,
            'patternMatch': patternMatch.value,
            'attributes': [
                attr.asDict()
                for attr in attributes
            ],
            'message': self.messageTextCtrl.Value,
            'offset': self.offsetEdit.Value,
            'snippet':snippet or self.snippet,
            'keystroke': self.keystroke,
            #'enableAutoSpeak': self.autoSpeakEnabledCheckBox.Value,
            'autoSpeakMode': self.getAutoSpeakMode(),
            'builtInWavFile': self.getBiw(),
        })
        return bookmark

    def makeNewSite(self):
        if not self.allowSiteSelection:
            return self.oldSite
        newSite = self.config.sites[self.siteComboBox.control.GetSelection()]
        if newSite != self.oldSite:
            result = gui.messageBox(
                _("Warning: you are about to move this bookmark to site %(new_site)s. "
                "This bookmark will disappear from the old site %(old_site)s. Would you like to proceed?") % {"new_site": newSite.getDisplayName(), "old_site": self.oldSite.getDisplayName()},
                _("Bookmark Entry warning"),
                wx.YES|wx.NO|wx.ICON_WARNING,
                self
            )
            if result == wx.YES:
                return newSite
            else:
                self.siteComboBox.control.SetFocus()
                return None
        return self.oldSite

    def onChar(self, event):
        keyCode = event.GetKeyCode ()
        if keyCode == 32: #space
            tones.beep(500, 50)
            index = self.availableAttributesListBox.control.Selection
            if index >= 0:
                item = self.attrChoices[index]
                s = self.attributesTextCtrl.GetValue()
                if len(s) > 0 and not s.endswith(' '):
                    s += ' '
                s += item
                self.attributesTextCtrl.SetValue(s)
                ui.message(_("Added '{item} to matched attributes edit box.'"))
        else:
            event.Skip()

    def getCategory(self):
        return list(BookmarkCategory)[self.categoryComboBox.control.GetSelection()]

    def onCategory(self, event):
        category = self.getCategory()
        self.updateCustomKeystrokeButtonLabel()
        self.messageTextCtrl.Disable() if category in {
            BookmarkCategory.SKIP_CLUTTER,
            BookmarkCategory.HIERARCHICAL,
            BookmarkCategory.SCRIPT,
            BookmarkCategory.NUMERIC_SCRIPT,
        } else self.messageTextCtrl.Enable()
        self.customeKeystrokeButton.Disable() if category in {
            BookmarkCategory.SKIP_CLUTTER,
            BookmarkCategory.HIERARCHICAL,
            BookmarkCategory.NUMERIC_SCRIPT,
        } else self.customeKeystrokeButton.Enable()

        self.patternTextCtrl.Disable() if category in {
            BookmarkCategory.SCRIPT,
            BookmarkCategory.NUMERIC_SCRIPT,
        } else self.patternTextCtrl.Enable()
        self.matchModeCategory.control.Disable() if category in {
            BookmarkCategory.SCRIPT,
            BookmarkCategory.NUMERIC_SCRIPT,
        } else self.matchModeCategory.control.Enable()
        self.offsetEdit.Disable() if category in {
            BookmarkCategory.SCRIPT,
        } else self.offsetEdit.Enable()
        self.attributesTextCtrl.Disable() if category in {
            BookmarkCategory.SCRIPT,
        } else self.attributesTextCtrl.Enable()
        self.autoSpeakModeComboBox.control.Enable() if category in {
            BookmarkCategory.QUICK_SPEAK,
            BookmarkCategory.QUICK_SPEAK_2,
        } else self.autoSpeakModeComboBox.control.Disable()

    def getAutoSpeakMode(self):
        result = list(AutoSpeakMode)[self.autoSpeakModeComboBox.control.GetSelection()]
        return result

    def onAutoSpeakMode(self, event):
        asm = self.getAutoSpeakMode()
        biwControls = [
            self.biwCategory,
            self.biwList,
        ]
        [biw.control.Enable() for biw in biwControls] if (
            asm.value.startswith("chime")
        ) else [biw.control.Disable() for biw in biwControls]

    def OnEditScriptClick(self,evt):
        _snippet = self.snippet
        _cursorLine, _cursorColumn = self.cursorLine, self.cursorColumn
        _good = False
        _cancel = False
        def onTextComplete(result, text, hasChanged, cursorLine, cursorColumn, keystroke):
            nonlocal _good, _cancel, _snippet, _cursorLine, _cursorColumn
            if result == wx.ID_OK:
                _cursorLine, _cursorColumn = cursorLine, cursorColumn
                _snippet = text
                tempRule = self.make(snippet=text, quiet=True)
                if tempRule.compileError is None:
                    tones.beep(500, 50)
                    _good = True
                else:
                    gui.messageBox(str(tempRule.compileError), _("Script compilation failed "), wx.OK|wx.ICON_WARNING, self)
                    _good = False
            else:
                _cancel = True

        title = _("Editing script for %s")
        title = title % self.bookmark.getDisplayName()
        while not _good and not _cancel:
            d = EditTextDialog(self, _snippet, _cursorLine, _cursorColumn, onTextComplete, title=title)
            result = d.ShowModal()
        if _good:
            self.snippet = _snippet
            self.cursorLine, self.cursorColumn = _cursorLine, _cursorColumn

    def updateCustomKeystrokeButtonLabel(self):
        keystroke = self.keystroke
        if keystroke:
            self.customeKeystrokeButton.SetLabel(_("Custom &Keystroke: %s") % (keystroke))
        else:
            self.customeKeystrokeButton.SetLabel(_("Default &Keystroke: %s") % (getDefaultKeystroke(self.getCategory())))
            #            if keystroke else _("Default (%s)"))) % 

    def OnCustomKeystrokeClick(self,evt):
        if inputCore.manager._captureFunc:
            # don't add while already in process of adding.
            return
        def addGestureCaptor(gesture: inputCore.InputGesture):
            if gesture.isModifier:
                return False
            inputCore.manager._captureFunc = None
            wx.CallAfter(self._addCaptured, gesture)
            return False
        inputCore.manager._captureFunc = addGestureCaptor
        core.callLater(50, ui.message, _("Press desired keystroke now"))

    blackListedKeystrokes = "escape enter numpadenter space nvda+space nvda+n nvda+q nvda+j j tab uparrow downarrow leftarrow rightarrow home end control+home control+end delete".split()

    def _addCaptured(self, gesture):
        api.g = gesture
        g = getKeystrokeFromGesture(gesture)
        if g in ["escape", "delete"]:
            self.keystroke = None
            msg = _("Keystroke reset to default")
        elif g  in self.blackListedKeystrokes:
            msg = _("Invalid keystroke %s: cannot overload essential  NVDA keystrokes!") % g
        elif self.bookmark.category.name.startswith('QUICK_JUMP') and 'shift+' in g:
            msg = _("Invalid keystroke %s: Cannot use keystrokes with shift modifier for quickJump bookmarks!") % g
        else:
            self.keystroke = g
            msg = None
        if msg:
            core.callLater(50, ui.message, msg)
        self.updateCustomKeystrokeButtonLabel()

    def getBiwCategories(self):
        soundsPath = utils.getSoundsPath()
        return [o for o in os.listdir(soundsPath)
            if os.path.isdir(os.path.join(soundsPath,o))
        ]

    def getBuiltInWaveFilesInCategory(self):
        soundsPath = utils.getSoundsPath()
        category = self.getBiwCategory()
        ext = ".wav"
        return [o for o in os.listdir(os.path.join(soundsPath, category))
            if not os.path.isdir(os.path.join(soundsPath,o))
                and o.lower().endswith(ext)
        ]

    def getBuiltInWaveFiles(self):
        soundsPath = utils.getSoundsPath()
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
        if biw is None:
            return
        category, biwFile = os.path.split(biw)
        categoryIndex = self.getBiwCategories().index(category)
        self.biwCategory.control.SetSelection(categoryIndex)
        self.onBiwCategory(None)
        biwIndex = self.getBuiltInWaveFilesInCategory().index(biwFile)
        self.biwList.control.SetSelection(biwIndex)

    def onBiw(self, evt):
        soundsPath = utils.getSoundsPath()
        biw = self.getBiw()
        fullPath = os.path.join(soundsPath, biw)
        nvwave.playWaveFile(fullPath)

    def getBiwCategory(self):
        return   self.getBiwCategories()[self.biwCategory.control.GetSelection()]

    def onBiwCategory(self, evt):
        soundsPath = utils.getSoundsPath()
        category = self.getBiwCategory()
        self.biwList.control.SetItems(self.getBuiltInWaveFilesInCategory())

    def onOk(self,evt):
        bookmark = self.make()
        if bookmark is not None:
            newSite = self.makeNewSite()
            if newSite is  not None:
                self.bookmark = bookmark
                self.newSite = newSite
                evt.Skip()

class BookmarksListDialog(
    gui.dpiScalingHelper.DpiScalingHelperMixinWithoutInit,
    wx.Dialog,
):
    def __init__(self, parent, site, config):
        title=_("Edit bookmarks for %s") % site.getDisplayName()
        super(BookmarksListDialog,self).__init__(parent,title=title)
        self.site = site
        self.bookmarks = list(site.bookmarks)
        self.config = config
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
      # Bookmarks table
        rulesText = _("&Bookmarks")
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
        self.rulesList.ItemCount = len(self.bookmarks)

        bHelper = sHelper.addItem(guiHelper.ButtonHelper(orientation=wx.HORIZONTAL))
      # Buttons
        self.addButton = bHelper.addButton(self, label=_("&Add"))
        self.addButton.Bind(wx.EVT_BUTTON, self.OnAddClick)
        self.editButton = bHelper.addButton(self, label=_("&Edit"))
        self.editButton.Bind(wx.EVT_BUTTON, self.OnEditClick)
        self.removeButton = bHelper.addButton(self, label=_("&Remove bookmark"))
        self.removeButton.Bind(wx.EVT_BUTTON, self.OnRemoveClick)
        self.moveUpButton = bHelper.addButton(self, label=_("Move &up"))
        self.moveUpButton.Bind(wx.EVT_BUTTON, lambda evt: self.OnMoveClick(evt, -1))
        self.moveDownButton = bHelper.addButton(self, label=_("Move &down"))
        self.moveDownButton.Bind(wx.EVT_BUTTON, lambda evt: self.OnMoveClick(evt, 1))
        self.sortButton = bHelper.addButton(self, label=_("&Sort"))
        self.sortButton.Bind(wx.EVT_BUTTON, self.OnSortClick)
      # OK/Cancel buttons
        sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))
        self.rulesList.SetFocus()

    def getItemTextForList(self, item, column):
        bookmark = self.bookmarks[item]
        if column == 0:
            return bookmark.getDisplayName()
        elif column == 1:
            return bookmark.pattern
        elif column == 2:
            return patterMatchNames[bookmark.patternMatch]
        elif column == 3:
            return BookmarkCategoryShortNames[bookmark.category]
        elif column == 4:
            return _('Enabled') if bookmark.enabled else _('Disabled')
        else:
            raise ValueError("Unknown column: %d" % column)

    def onListItemFocused(self, evt):
        if self.rulesList.GetSelectedItemCount()!=1:
            return
        index=self.rulesList.GetFirstSelected()
        bookmark = self.bookmarks[index]

    def OnAddClick(self,evt):
        entryDialog=EditBookmarkDialog(
            self,
            config=self.config,
            site=self.site,
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            self.bookmarks.append(entryDialog.bookmark)
            self.rulesList.ItemCount = len(self.bookmarks)
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
        entryDialog=EditBookmarkDialog(
            self,
            bookmark=self.bookmarks[editIndex],
            config=self.config,
            site=self.site,
            allowSiteSelection=True,
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            if self.site != entryDialog.newSite:
                # moving to newSite!
                del self.bookmarks[editIndex]
                #self.rulesList.DeleteItem(editIndex)
                self.rulesList.ItemCount = len(self.bookmarks)
                newSite = entryDialog.newSite
                bookmarks = list(newSite.bookmarks)
                bookmarks.append(entryDialog.bookmark)
                newSite2 = newSite.updateBookmarks(bookmarks)
                sites = list(self.config.sites)
                index = sites.index(newSite)
                sites[index] = newSite2
                self.config = self.config.updateSites(sites)
            else:
                self.bookmarks[editIndex] = entryDialog.bookmark
            self.rulesList.SetFocus()
        entryDialog.Destroy()

    def OnRemoveClick(self,evt):
        index=self.rulesList.GetFirstSelected()
        while index>=0:
            self.rulesList.DeleteItem(index)
            del self.bookmarks[index]
            index=self.rulesList.GetNextSelected(index)
        self.rulesList.SetFocus()

    def OnMoveClick(self,evt, increment):
        if self.rulesList.GetSelectedItemCount()!=1:
            return
        index=self.rulesList.GetFirstSelected()
        if index<0:
            return
        newIndex = index + increment
        if 0 <= newIndex < len(self.bookmarks):
            # Swap
            tmp = self.bookmarks[index]
            self.bookmarks[index] = self.bookmarks[newIndex]
            self.bookmarks[newIndex] = tmp
            self.rulesList.Select(newIndex)
            self.rulesList.Focus(newIndex)
        else:
            return

    def OnSortClick(self,evt):
        self.bookmarks.sort(key=QJSite.getDisplayName)

    def onOk(self,evt):
        evt.Skip()

class EditSiteDialog(wx.Dialog):
    def __init__(self, parent, site=None, config=None, knownSites=None, url=None, domain=None):
        title=_("Edit site configuration")
        super(EditSiteDialog,self).__init__(parent,title=title)
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        if site is  not None:
            self.site = site
        else:
            self.site = QJSite({
                'domain':domain or url or "",
                'name':'',
                'urlMatch':URLMatch.EXACT.value if url is not None else URLMatch.SUBDOMAIN.value,
                'focusMode':FocusMode.UNCHANGED.value,
                'liveRegionMode':LiveRegionMode.UNCHANGED.value,
                'debugBeepMode':DebugBeepMode.NO_BEEPS.value,
                'bookmarks': [],
                'autoClickOnFocus': False,
                'autoClickCategory': BookmarkCategory.QUICK_CLICK,
                'autoClickOnFocusDelay': 500,
                'autoClickContinuous': False,
                'autoClickContinuousDelay': 500,
            })
        self.config = config
        self.knownSites = knownSites
      # Translators: label for comment edit box
        commentLabelText = _("&Display name (optional)")
        self.commentTextCtrl=sHelper.addLabeledControl(commentLabelText, wx.TextCtrl)
        self.commentTextCtrl.SetValue(self.site.name)
      # Translators: domain
        patternLabelText = _("&URL")
        self.patternTextCtrl=sHelper.addLabeledControl(patternLabelText, wx.TextCtrl)
        self.patternTextCtrl.SetValue(self.site.domain)
      # Translators:  label for type selector radio buttons
        typeText = _("&Match type")
        self.typeComboBox = guiHelper.LabeledControlHelper(
            self,
            typeText,
            wx.Choice,
            choices=[urlMatchNames[i] for i in URLMatch],
        )
        self.typeComboBox.control.SetSelection(list(URLMatch).index(self.site.urlMatch))

      # Edit bookmarks button
        self.editRulesButton = sHelper.addItem (wx.Button (self, label = _("Edit &bookmarks")))
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
        self.focusModeCategory.control.SetSelection(list(FocusMode).index(self.site.focusMode))
      # Translators: Live region Mode comboBox
        labelText=_("&Live region mode")
        self.liveRegionModeCategory=guiHelper.LabeledControlHelper(
            self,
            labelText,
            wx.Choice,
            choices=[
                liveRegionModeNames[m]
                for m in LiveRegionMode
            ],
        )
        self.liveRegionModeCategory.control.SetSelection(list(LiveRegionMode).index(self.site.liveRegionMode))
      # Translators: Debug Beep  comboBox
        labelText=_("Debug &beep mode")
        self.debugBeepModeCategory=guiHelper.LabeledControlHelper(
            self,
            labelText,
            wx.Choice,
            choices=[
                debugBeepModeNames[m]
                for m in DebugBeepMode
            ],
        )
        self.debugBeepModeCategory.control.SetSelection(list(DebugBeepMode).index(self.site.debugBeepMode))
      # Translators:  AutoClick on load combo box
        text = _("Perform autoClick on page load automatically:")
        self.autoClickOptions = [
            None,
            BookmarkCategory.QUICK_CLICK,
            BookmarkCategory.QUICK_CLICK_2,
            BookmarkCategory.QUICK_CLICK_3,
        ]
        self.autoClickComboBox = guiHelper.LabeledControlHelper(
            self,
            text,
            wx.Choice,
            choices=[BookmarkCategoryShortNames.get(option, _("Disabled"))  for option in self.autoClickOptions],
        )
        self.autoClickComboBox.control.Bind(wx.EVT_CHOICE,self.onAutoClickCombo)
        self.autoClickComboBox.control.SetSelection(self.autoClickOptions.index(
            self.site.autoClickCategory if self.    site.autoClickOnFocus else None
        ))
      # Initial delay spin
        labelText = _("Delay before initial autoClick in milliseconds:")
        self.delayEdit = sHelper.addLabeledControl(
            labelText, nvdaControls.SelectOnFocusSpinCtrl,
            min=1, max=10000,
            initial=self.site.autoClickOnFocusDelay,
        )
      # Translators: label for enable recurrent auto click checkbox
        Text = _("Enable recurrent auto click")
        self.recurrentCheckBox=sHelper.addItem(wx.CheckBox(self,label=Text))
        self.recurrentCheckBox.Bind(wx.EVT_CHECKBOX,self.onRecurrent)
        self.recurrentCheckBox.SetValue(self.site.autoClickContinuous)
      # Recurrent  delay spin
        labelText = _("Delay between recurring autoClicks  in milliseconds:")
        self.recurrentDelayEdit = sHelper.addLabeledControl(
            labelText, nvdaControls.SelectOnFocusSpinCtrl,
            min=1, max=10000,
            initial=self.site.autoClickContinuousDelay,
        )
      # Translators: label for enable recurrent autoSpeak
        if False:
            Text = _("Enable recurrent auto speak of ")
            self.autoSpeakCheckBox=sHelper.addItem(wx.CheckBox(self,label=Text))
            self.autoSpeakCheckBox.Bind(wx.EVT_CHECKBOX,self.onRecurrent)
            self.autoSpeakCheckBox.SetValue(self.site.autoSpeak)
      # Translators:  autoSpeak combo box
        if False:
            text = _("Perform autoSpeak (live region) for:")
            self.autoSpeakOptions = [
                None,
                BookmarkCategory.QUICK_SPEAK,
                BookmarkCategory.QUICK_SPEAK_2,
            ]
            self.autoSpeakComboBox = guiHelper.LabeledControlHelper(
                self,
                text,
                wx.Choice,
                choices=[BookmarkCategoryShortNames.get(option, _("Disabled"))  for option in self.autoSpeakOptions],
            )
            self.autoSpeakComboBox.control.Bind(wx.EVT_CHOICE,self.onAutoSpeakCombo)
            self.autoSpeakComboBox.control.SetSelection(self.autoClickOptions.index(
                self.site.autoSpeakCategory if self.    site.autoSpeak else None
            ))
      # Translators: label for enable recurrent auto click checkbox
        Text = _("Suppress descriptions")
        self.suppressDescriptionCheckBox=sHelper.addItem(wx.CheckBox(self,label=Text))
        self.suppressDescriptionCheckBox.SetValue(self.site.suppressDescription)
      #  OK/cancel buttons
        sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))

        mainSizer.Add(sHelper.sizer,border=20,flag=wx.ALL)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        self.patternTextCtrl.SetFocus()
        self.Bind(wx.EVT_BUTTON,self.onOk,id=wx.ID_OK)

        self.onAutoClickCombo(None)

    def make(self):
        urlMatch = list(URLMatch)[self.typeComboBox.control.GetSelection()]
        domain = self.patternTextCtrl.Value
        errorMsg = None
        if urlMatch in [URLMatch.IGNORE, URLMatch.EMPTY]:
            if len(domain) > 0:
                errorMsg = _("You must specify blank domain for this match option.")
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
                except re.error as e:
                    errorMsg = _("Failed to compile regular expression: %s") % str(e)

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
            gui.messageBox(errorMsg, _("Site Entry Error"), wx.OK|wx.ICON_WARNING, self)
            self.patternTextCtrl.SetFocus()
            return
        if urlMatch in {URLMatch.DOMAIN, URLMatch.SUBDOMAIN}:
            domain = domain.lower()
        site = QJSite({
            'domain':domain,
            'urlMatch':urlMatch,
            'name':self.commentTextCtrl.Value,
            'focusMode': list(FocusMode)[self.focusModeCategory.control.GetSelection()],
            'liveRegionMode': list(LiveRegionMode)[self.liveRegionModeCategory.control.GetSelection()],
            'debugBeepMode': list(DebugBeepMode)[self.debugBeepModeCategory.control.GetSelection()],
            'bookmarks': [
                b.asDict()
                for b in self.site.bookmarks
            ],
            'autoClickOnFocus': self.getAutoClickCombo() is not None,
            'autoClickCategory': (self.getAutoClickCombo() or BookmarkCategory.QUICK_CLICK).value,
            'autoClickOnFocusDelay': self.delayEdit.Value,
            'autoClickContinuous': self.recurrentCheckBox.Value,
            'autoClickContinuousDelay': self.recurrentDelayEdit.Value,
            #'autoSpeak': self.getAutoSpeakCombo() is not None,
            #'autoSpeakCategory': (self.getAutoSpeakCombo() or BookmarkCategory.QUICK_SPEAK).value,
            'suppressDescription': self.suppressDescriptionCheckBox.Value,
        })
        return site

    def OnEditRulesClick(self,evt):
        mylog(f"EditSiteDialog.editBookmarks nb={len(self.site.bookmarks)}")
        entryDialog=BookmarksListDialog(
            self,
            site=self.site,
            config=self.config,
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            self.site = self.site.updateBookmarks(entryDialog.bookmarks)
            self.config = entryDialog.config
            mylog(f"EditSiteDialog.editBookmarks2 nb={len(self.site.bookmarks)}")
        entryDialog.Destroy()
    def getAutoClickCombo(self):
        return self.autoClickOptions[self.autoClickComboBox.control.GetSelection()]

    def onAutoClickCombo(self, event):
        category = self.getAutoClickCombo()
        for control in [
            self.delayEdit,
            self.recurrentCheckBox,
            self.recurrentDelayEdit,
        ]:
            if category is None:
                control.Disable()
            else:
                control.Enable()
        self.onRecurrent(event)

    def getAutoSpeakCombo(self):
        return self.autoSpeakOptions[self.autoSpeakComboBox.control.GetSelection()]

    def onAutoSpeakCombo(self, event):
        pass

    def onRecurrent(self, event):
        enabled = self.recurrentCheckBox.Value
        if enabled:
            self.recurrentDelayEdit.Enable()
        else:
            self.recurrentDelayEdit.Disable()

    def onOk(self,evt):
        site = self.make()
        if site is not None:
            self.site = site
            evt.Skip()


class SettingsDialog(SettingsPanel):
    title = _("BrowserNav QuickSearch websites and bookmarks")

    def __init__(self, *args, **kwargs):
        super(SettingsDialog, self).__init__(*args, **kwargs)

    def makeSettings(self, settingsSizer):
        global globalConfig
        self.config = copy.deepcopy(globalConfig)

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
        self.editRulesButton = bHelper.addButton(self, label=_("Edit &bookmarks"))
        self.editRulesButton.Bind(wx.EVT_BUTTON, self.OnEditRulesClick)
        self.removeButton = bHelper.addButton(self, label=_("&Remove site"))
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
        entryDialog=EditSiteDialog(self, knownSites=self.config.sites, config=self.config)
        if entryDialog.ShowModal()==wx.ID_OK:
            sites = list(self.config.sites) + [entryDialog.site]
            self.config = entryDialog.config
            self.config = self.config.updateSites(sites)
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
            config=self.config,
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            self.config = entryDialog.config
            sites = list(self.config.sites)
            sites[editIndex] = entryDialog.site
            self.config = self.config.updateSites(sites)
            self.sitesList.SetFocus()
        entryDialog.Destroy()

    def OnEditRulesClick(self,evt):
        if self.sitesList.GetSelectedItemCount()!=1:
            return
        editIndex=self.sitesList.GetFirstSelected()
        if editIndex<0:
            return
        entryDialog=BookmarksListDialog(
            self,
            site=self.config.sites[editIndex],
            config=self.config,
        )
        if entryDialog.ShowModal()==wx.ID_OK:
            self.config = entryDialog.config
            sites = list(self.config.sites)
            sites[editIndex] = sites[editIndex].updateBookmarks(entryDialog.bookmarks)
            self.config = self.config.updateSites(sites)
            self.sitesList.SetFocus()
        entryDialog.Destroy()

    def OnRemoveClick(self,evt):
        sites = list(self.config.sites)
        index=self.sitesList.GetFirstSelected()
        while index>=0:
            self.sitesList.DeleteItem(index)
            del sites[index]
            index=self.sitesList.GetNextSelected(index)
        self.config = self.config.updateSites(sites)
        self.sitesList.SetFocus()

    def OnMoveClick(self,evt, increment):
        if self.sitesList.GetSelectedItemCount()!=1:
            return
        index=self.sitesList.GetFirstSelected()
        if index<0:
            return
        newIndex = index + increment
        if 0 <= newIndex < len(self.config.sites):
            sites = list(self.config.sites)
            # Swap
            tmp = sites[index]
            sites[index] = sites[newIndex]
            sites[newIndex] = tmp
            self.config = self.config.updateSites(sites)
            self.sitesList.Select(newIndex)
            self.sitesList.Focus(newIndex)
        else:
            return

    def OnSortClick(self,evt):
        sites = list(self.config.sites)
        sites.sort(key=QJSite.getDisplayName)
        self.config = self.config.updateSites(sites)

    def onSave(self):
        global globalConfig
        globalConfig = self.config
        saveConfig()
