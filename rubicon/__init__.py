from pkgutil import extend_path
import os

__path__ = extend_path(__path__, __name__)

vendor_path = os.path.join(os.path.dirname(__file__), "..", "rubicon_vendor", "rubicon")
vendor_path = os.path.abspath(vendor_path)
if os.path.isdir(vendor_path) and vendor_path not in __path__:
    __path__.append(vendor_path)
