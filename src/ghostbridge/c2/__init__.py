"""
GhostBridge C2 Module

Command & Control integration with MoMo platform.
"""

from ghostbridge.c2.beacon import BeaconService
from ghostbridge.c2.client import MoMoClient

__all__ = [
    "BeaconService",
    "MoMoClient",
]

