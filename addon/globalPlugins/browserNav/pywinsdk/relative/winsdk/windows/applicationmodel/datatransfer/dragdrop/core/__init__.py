# WARNING: Please don't edit this file. It was generated by Python/WinRT v1.0.0-beta.6

import enum

from .......  import winsdk

_ns_module = winsdk._import_ns_module("Windows.ApplicationModel.DataTransfer.DragDrop.Core")

try:
    from ....  import datatransfer
except ImportError:
    pass

try:
    from ...  import dragdrop
except ImportError:
    pass

try:
    from .....  import foundation
except ImportError:
    pass

try:
    from ..... graphics import imaging
except ImportError:
    pass

class CoreDragUIContentMode(enum.IntFlag):
    AUTO = 0
    DEFERRED = 0x1

_ns_module._register_CoreDragUIContentMode(CoreDragUIContentMode)

CoreDragDropManager = _ns_module.CoreDragDropManager
CoreDragInfo = _ns_module.CoreDragInfo
CoreDragOperation = _ns_module.CoreDragOperation
CoreDragUIOverride = _ns_module.CoreDragUIOverride
CoreDropOperationTargetRequestedEventArgs = _ns_module.CoreDropOperationTargetRequestedEventArgs
ICoreDropOperationTarget = _ns_module.ICoreDropOperationTarget
