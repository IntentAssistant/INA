"""
Vendored dependencies that must ship with the packaged app bundle.

Py2app relies on the legacy ``imp`` loader which does not understand implicit
namespace packages, so we provide a conventional package initializer to keep
imports working both at build time and at runtime.
"""

# Intentionally empty – the package only serves as a namespace for vendored code.
