#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import controlTypes
import core
import _ctypes
import IAccessibleHandler
from queue import Queue
import threading
from threading import Thread
from threading import Lock, Condition
import tones
import types
from virtualBuffers.gecko_ia2 import Gecko_ia2_TextInfo
import weakref
import winUser

def weakMemoize(func):
    cache = weakref.WeakKeyDictionary()

    def memoized_func(*args):
        arg = args[0]
        if len(args) > 1:
            raise Exception("Only supports single argument!")
        value = cache.get(arg)
        if value is not None:
            return value
        result = func(*args)
        cache.update({arg: result})
        return result

    return memoized_func

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

    def done(self):
        return self.__is_set


def getIA2Document(textInfo):
    # IAccessibleHandler.getRecursiveTextFromIAccessibleTextObject(IAccessibleHandler.normalizeIAccessible(pacc1.accParent))
    ia = textInfo.NVDAObjectAtStart.IAccessibleObject
    for i in range(1000):
        try:
            if controlTypes.ROLE_DOCUMENT == IAccessibleHandler.IAccessibleRolesToNVDARoles[ia.accRole(winUser.CHILDID_SELF)]:
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
# For quick finding paragraphs, llok at:
# VirtualBufferTextInfo._getParagraphOffsets