from pkgutil import extend_path

# Make sure the namespace package works when bundled.
__path__ = extend_path(__path__, __name__)
