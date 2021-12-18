#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import controlTypes
import core
import IAccessibleHandler
from queue import Queue
import threading
from threading import Thread
import tones
import types
from virtualBuffers.gecko_ia2 import Gecko_ia2_TextInfo
import winUser

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


def getGeckoParagraphIndent(textInfo, document=None):
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
        if document is None:
            document = getIA2Document(textInfo)
        offset = textInfo._startOffset
        docHandle,ID=textInfo._getFieldIdentifierFromOffset(offset)
        location = document.accLocation(ID)
        return location[0]
    except WindowsError:
        tones.beep(500, 50)
        return None
    except LookupError:
        tones.beep(500, 50)
        return None
# For quick finding paragraphs, llok at:
# VirtualBufferTextInfo._getParagraphOffsets