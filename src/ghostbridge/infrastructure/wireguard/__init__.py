"""
WireGuard Infrastructure Module

WireGuard VPN tunnel management for secure C2 communication.
"""

from ghostbridge.infrastructure.wireguard.config import WireGuardConfig
from ghostbridge.infrastructure.wireguard.manager import WireGuardManager

__all__ = [
    "WireGuardManager",
    "WireGuardConfig",
]

