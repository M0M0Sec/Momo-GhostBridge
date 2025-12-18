"""
GhostBridge - Transparent Network Implant for Red Team Persistence

A stealthy network bridge device that provides persistent access
to target networks through encrypted tunnels.
"""

__version__ = "0.5.0"
__author__ = "MoMo Team"

from ghostbridge.core.config import GhostBridgeConfig
from ghostbridge.main import GhostBridge

__all__ = [
    "__version__",
    "GhostBridge",
    "GhostBridgeConfig",
]

