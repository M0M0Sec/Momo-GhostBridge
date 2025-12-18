"""
WireGuard Infrastructure Module

WireGuard VPN tunnel management for secure C2 communication.
"""

from ghostbridge.infrastructure.wireguard.manager import WireGuardManager
from ghostbridge.infrastructure.wireguard.config import WireGuardConfig

__all__ = [
    "WireGuardManager",
    "WireGuardConfig",
]

