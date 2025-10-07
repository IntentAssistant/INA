from pkgutil import extend_path

# Ensure package namespace can be discovered by tools like py2app
__path__ = extend_path(__path__, __name__)
