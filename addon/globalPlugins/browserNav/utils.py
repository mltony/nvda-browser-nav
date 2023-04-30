#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

from .constants import *
import controlTypes
import core
import _ctypes
from enum import Enum
import IAccessibleHandler
from queue import Queue
import speech
import textInfos
import threading
from threading import Thread
from threading import Lock, Condition
import time
import tones
import types
from virtualBuffers.gecko_ia2 import Gecko_ia2_TextInfo
import weakref
import ui
import winUser

class FakeObjectForWeakMemoize:
    pass

NoneObjectForWeakRef = FakeObjectForWeakMemoize()

def weakMemoize(func, timeoutSecs=0):
    cache = weakref.WeakKeyDictionary()

    def memoized_func(*args):
        arg = args[0]
        if len(args) > 1:
            raise Exception("Only supports single argument!")
        if arg is None:
            # Cannot create weak reference to None
            arg = NoneObjectForWeakRef
        timestamp,value = cache.get(arg, (None, None))
        if (
            value is not None
            and (
                timeoutSecs == 0
                or time.time() - timestamp < timeoutSecs
            )
        ):
            return value
        result = func(*args)
        timestamp = time.time()
        cache.update({arg: (timestamp,result)})
        return result

    return memoized_func

def weakMemoizeWithTimeout(timeoutSecs):
    return lambda func: weakMemoize(func, timeoutSecs)

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
    core.callLater(value, executeAsynchronously, gen)

class Worker(Thread):
    """ Thread executing tasks from a given tasks queue """
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()
    def run(self):
        while True:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception as e:
                # An exception happened in this thread
                log.error("Error in ThreadPool ", e)
            finally:
                # Mark this task as done, whether an exception happened or not
                self.tasks.task_done()


class ThreadPool:
    """ Pool of threads consuming tasks from a queue """
    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)
    def add_task(self, func, *args, **kargs):
        """ Add a task to the queue """
        self.tasks.put((func, args, kargs))
    def map(self, func, args_list):
        """ Add a list of tasks to the queue """
        for args in args_list:
            self.add_task(func, args)
    def wait_completion(self):
        """ Wait for completion of all the tasks in the queue """
        self.tasks.join()


threadPool = ThreadPool(5)



class Future:
    def __init__(self):
        self.__condition = Condition(Lock())
        self.__val = None
        self.__exc = None
        self.__is_set = False

    def get(self):
        with self.__condition:
            while not self.__is_set:
                self.__condition.wait()
            if self.__exc is not None:
                raise self.__exc
            return self.__val

    def set(self, val):
        with self.__condition:
            if self.__is_set:
                raise RuntimeError("Future has already been set")
            self.__val = val
            self.__is_set = True
            self.__condition.notify_all()

    def setException(self, val):
        with self.__condition:
            if self.__is_set:
                raise RuntimeError("Future has already been set")
            self.__exc = val
            self.__is_set = True
            self.__condition.notify_all()
            
    def isSet(self):
        return self.__is_set

    def done(self):
        return self.__is_set


def getIA2Document(textInfo):
    # IAccessibleHandler.getRecursiveTextFromIAccessibleTextObject(IAccessibleHandler.normalizeIAccessible(pacc1.accParent))
    ia = textInfo.NVDAObjectAtStart.IAccessibleObject
    for i in range(1000):
        try:
            if ROLE_DOCUMENT == IAccessibleHandler.IAccessibleRolesToNVDARoles[ia.accRole(winUser.CHILDID_SELF)]:
                return ia
        except KeyError:
            pass
        ia=IAccessibleHandler.normalizeIAccessible(ia.accParent)
    raise Exception("Infinite loop!")


class DocumentHolder:
    def __init__(self, document):
        self.document = document

def getGeckoParagraphIndent(textInfo, documentHolder=None, oneLastAttempt=False):
    if not isinstance(textInfo, Gecko_ia2_TextInfo):
        raise Exception("This function only works with Gecko_ia2_TextInfo")
    # This is an optimized version of flow for Chrome and Firefox browsers, that avoids creating NVDAObject for performance reasons.
    # The original flow goes like this:
    # OffsetsTextInfo._get_NVDAObjectAtStart()
    # VirtualBufferTextInfo._getNVDAObjectFromOffset()
    # Gecko_ia2.getNVDAObjectFromIdentifier
    # NVDAObjects.IAccessible.getNVDAObjectFromEvent
    # IAccessibleHandler.accessibleObjectFromEvent
    # oleacc.AccessibleObjectFromEvent
    # In order to optimize performance we query IAccessible document.
    # This allows us to have a single IAccessible object and query locations of all its children without the need to create multiple objects.
    try:
        if documentHolder is None:
            document = getIA2Document(textInfo)
        else:
            document = documentHolder.document
        offset = textInfo._startOffset
        docHandle,ID=textInfo._getFieldIdentifierFromOffset(offset)
        location = document.accLocation(ID)
        return location[0]
    except WindowsError:
        return None
    except LookupError:
        return None
    except _ctypes.COMError:
        if oneLastAttempt or documentHolder is None:
            return None
        # This tends to happen when page changes dynamically.
        # We need to retry by recreating document and storing a new copy of it in the document holder.
        documentHolder.document = getIA2Document(textInfo)
        return getGeckoParagraphIndent(textInfo, documentHolder, oneLastAttempt=True)
        
        return None
# For quick finding paragraphs, look at:
# VirtualBufferTextInfo._getParagraphOffsets

# Role constants changed in NVDA v2022 so we need to decode the old values.
class NVDA2021Role(Enum):
    UNKNOWN = 0
    WINDOW = 1
    TITLEBAR = 2
    PANE = 3
    DIALOG = 4
    CHECKBOX = 5
    RADIOBUTTON = 6
    STATICTEXT = 7
    EDITABLETEXT = 8
    BUTTON = 9
    MENUBAR = 10
    MENUITEM = 11
    POPUPMENU = 12
    COMBOBOX = 13
    LIST = 14
    LISTITEM = 15
    GRAPHIC = 16
    HELPBALLOON = 17
    TOOLTIP = 18
    LINK = 19
    TREEVIEW = 20
    TREEVIEWITEM = 21
    TAB = 22
    TABCONTROL = 23
    SLIDER = 24
    PROGRESSBAR = 25
    SCROLLBAR = 26
    STATUSBAR = 27
    TABLE = 28
    TABLECELL = 29
    TABLECOLUMN = 30
    TABLEROW = 31
    TABLECOLUMNHEADER = 32
    TABLEROWHEADER = 33
    FRAME = 34
    TOOLBAR = 35
    DROPDOWNBUTTON = 36
    CLOCK = 37
    SEPARATOR = 38
    FORM = 39
    HEADING = 40
    HEADING1 = 41
    HEADING2 = 42
    HEADING3 = 43
    HEADING4 = 44
    HEADING5 = 45
    HEADING6 = 46
    PARAGRAPH = 47
    BLOCKQUOTE = 48
    TABLEHEADER = 49
    TABLEBODY = 50
    TABLEFOOTER = 51
    DOCUMENT = 52
    ANIMATION = 53
    APPLICATION = 54
    BOX = 55
    GROUPING = 56
    PROPERTYPAGE = 57
    CANVAS = 58
    CAPTION = 59
    CHECKMENUITEM = 60
    DATEEDITOR = 61
    ICON = 62
    DIRECTORYPANE = 63
    EMBEDDEDOBJECT = 64
    ENDNOTE = 65
    FOOTER = 66
    FOOTNOTE = 67
    GLASSPANE = 69
    HEADER = 70
    IMAGEMAP = 71
    INPUTWINDOW = 72
    LABEL = 73
    NOTE = 74
    PAGE = 75
    RADIOMENUITEM = 76
    LAYEREDPANE = 77
    REDUNDANTOBJECT = 78
    ROOTPANE = 79
    EDITBAR = 80
    TERMINAL = 82
    RICHEDIT = 83
    RULER = 84
    SCROLLPANE = 85
    SECTION = 86
    SHAPE = 87
    SPLITPANE = 88
    VIEWPORT = 89
    TEAROFFMENU = 90
    TEXTFRAME = 91
    TOGGLEBUTTON = 92
    BORDER = 93
    CARET = 94
    CHARACTER = 95
    CHART = 96
    CURSOR = 97
    DIAGRAM = 98
    DIAL = 99
    DROPLIST = 100
    SPLITBUTTON = 101
    MENUBUTTON = 102
    DROPDOWNBUTTONGRID = 103
    MATH = 104
    GRIP = 105
    HOTKEYFIELD = 106
    INDICATOR = 107
    SPINBUTTON = 108
    SOUND = 109
    WHITESPACE = 110
    TREEVIEWBUTTON = 111
    IPADDRESS = 112
    DESKTOPICON = 113
    INTERNALFRAME = 115
    DESKTOPPANE = 116
    OPTIONPANE = 117
    COLORCHOOSER = 118
    FILECHOOSER = 119
    FILLER = 120
    MENU = 121
    PANEL = 122
    PASSWORDEDIT = 123
    FONTCHOOSER = 124
    LINE = 125
    FONTNAME = 126
    FONTSIZE = 127
    BOLD = 128
    ITALIC = 129
    UNDERLINE = 130
    FGCOLOR = 131
    BGCOLOR = 132
    SUPERSCRIPT = 133
    SUBSCRIPT = 134
    STYLE = 135
    INDENT = 136
    ALIGNMENT = 137
    ALERT = 138
    DATAGRID = 139
    DATAITEM = 140
    HEADERITEM = 141
    THUMB = 142
    CALENDAR = 143
    VIDEO = 144
    AUDIO = 145
    CHARTELEMENT = 146
    DELETED_CONTENT = 147
    INSERTED_CONTENT = 148
    LANDMARK = 149
    ARTICLE = 150
    REGION = 151
    FIGURE = 152
    MARKED_CONTENT = 153

def speakMessage(message):
    if message is None:
        return
    if isinstance(message, str):
        if not speech.isBlank(message):
            ui.message(message)
    elif isinstance(message, textInfos.TextInfo):
        speech.speakTextInfo(message, reason=controlTypes.OutputReason.CARET)
    else:
        raise RuntimeError(f"speakMessage got unsupported argument of type {type(message)}.")
    
allModifiers = [
    winUser.VK_LCONTROL, winUser.VK_RCONTROL,
    winUser.VK_LSHIFT, winUser.VK_RSHIFT, winUser.VK_LMENU,
    winUser.VK_RMENU, winUser.VK_LWIN, winUser.VK_RWIN,
]

def getCurrentModifiers():
    status = [
        k
        for k in allModifiers
        if winUser.getKeyState(k) & 32768 > 0
    ]
    return status

def waitForModifiersToBeReleased(timeoutSecs=1):
    t0 = time.time()
    t1 = t0 + timeoutSecs
    while True:
        if time.time() > t1:
            raise TimeoutError()
        status = [
            winUser.getKeyState(k) & 32768
            for k in allModifiers
        ]
        if not any(status):
            return
        yield 1
