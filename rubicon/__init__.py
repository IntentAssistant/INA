from pkgutil import extend_path

# Namespace package shim so packaging tools (e.g., py2app) can locate rubicon modules
__path__ = extend_path(__path__, __name__)
