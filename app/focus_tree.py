"""Public Focus Tree screen entry point.

``ModBrowserTab`` remains the compatibility implementation while its
behaviour is being migrated into focused modules.  New callers should import
``FocusTreeTab`` from here so the screen can evolve without changing the
application's navigation contract.
"""

from app.mod_browser import ModBrowserTab


FocusTreeTab = ModBrowserTab

__all__ = ["FocusTreeTab"]
