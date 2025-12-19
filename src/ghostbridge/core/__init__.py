"""
GhostBridge Core Module

Contains the core logic for bridge management, configuration,
tunnel management, and stealth operations.
"""

from ghostbridge.core.bridge import BridgeManager
from ghostbridge.core.config import GhostBridgeConfig
from ghostbridge.core.stealth import StealthLevel, StealthManager, ThreatLevel
from ghostbridge.core.tunnel import ConnectionState, TunnelManager

__all__ = [
    "GhostBridgeConfig",
    "BridgeManager",
    "TunnelManager",
    "ConnectionState",
    "StealthManager",
    "StealthLevel",
    "ThreatLevel",
]

