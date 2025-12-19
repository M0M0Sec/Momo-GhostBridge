"""
GhostBridge Infrastructure Module

System-level integrations including:
- Network management (iproute2, bridge-utils)
- WireGuard tunnel management
- System utilities (RAM disk, secure wipe)
"""

from ghostbridge.infrastructure.network import NetworkManager
from ghostbridge.infrastructure.system import RAMDiskManager, SecureWiper
from ghostbridge.infrastructure.wireguard import WireGuardConfig, WireGuardManager

__all__ = [
    "NetworkManager",
    "WireGuardManager",
    "WireGuardConfig",
    "RAMDiskManager",
    "SecureWiper",
]

