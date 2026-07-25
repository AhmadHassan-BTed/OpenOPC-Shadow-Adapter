"""openopc-shadow-adapter — Human-in-the-loop Shadow Mode for OpenOPC."""

from __future__ import annotations

from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.api.app import start_server_in_thread

__version__ = "0.1.0"
__all__ = ["ShadowModeAdapter", "__version__", "start_server_in_thread"]
