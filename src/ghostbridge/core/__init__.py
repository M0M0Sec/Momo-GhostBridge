"""
GhostBridge Core Module

Contains the core logic for bridge management, configuration,
tunnel management, and stealth operations.
"""

from ghostbridge.core.config import GhostBridgeConfig
from ghostbridge.core.bridge import BridgeManager
from ghostbridge.core.tunnel import TunnelManager, ConnectionState
from ghostbridge.core.stealth import StealthManager, StealthLevel, ThreatLevel

__all__ = [
    "GhostBridgeConfig",
    "BridgeManager",
    "TunnelManager",
    "ConnectionState",
    "StealthManager",
    "StealthLevel",
    "ThreatLevel",
]

