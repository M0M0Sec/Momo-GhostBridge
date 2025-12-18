"""
System Infrastructure Module

System-level operations including:
- RAM disk management
- Secure wiping
- Process management
- Hardware interfaces
"""

from ghostbridge.infrastructure.system.ramfs import RAMDiskManager
from ghostbridge.infrastructure.system.wipe import SecureWiper

__all__ = [
    "RAMDiskManager",
    "SecureWiper",
]

