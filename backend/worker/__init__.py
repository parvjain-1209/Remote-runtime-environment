# Worker package marker
import sys
from . import worker
from .worker import *

# Ensure attributes patched on the worker package propagate to worker.worker
class _WorkerModule(sys.modules[__name__].__class__):
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        try:
            setattr(worker, name, value)
        except Exception:
            pass

sys.modules[__name__].__class__ = _WorkerModule
