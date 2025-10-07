from pkgutil import extend_path

# Enable namespace-style discovery for the ``google`` package when bundled.
__path__ = extend_path(__path__, __name__)
