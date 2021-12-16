#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import controlTypes
import IAccessibleHandler
from queue import Queue
import threading
from threading import Thread
import tones
from virtualBuffers.gecko_ia2 import Gecko_ia2_TextInfo
import winUser



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
