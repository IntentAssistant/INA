"""
Local copy of ``rubicon`` that is bundled with the app.

Py2app requires a classic package layout with an ``__init__`` module so we
expose the ``objc`` subpackage just like the upstream project does.
"""

from importlib import import_module

# Re-export the objc package to match the public API of rubicon-objc.
objc = import_module(".objc", package=__name__)

__all__ = ["objc"]
