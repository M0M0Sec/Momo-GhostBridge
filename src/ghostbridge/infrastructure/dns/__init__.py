"""
DNS Tunneling Infrastructure.

Provides DNS-based covert communication when other channels are blocked.
Uses DNS TXT/CNAME/NULL records for data exfiltration.
"""

from ghostbridge.infrastructure.dns.client import (
    DNSClient,
    DNSQuery,
    DNSRecord,
)
from ghostbridge.infrastructure.dns.encoder import (
    Base32Encoder,
    Base64Encoder,
    DNSEncoder,
)
from ghostbridge.infrastructure.dns.tunnel import (
    DNSTunnel,
    DNSTunnelConfig,
    DNSTunnelState,
)

__all__ = [
    # Tunnel
    "DNSTunnel",
    "DNSTunnelConfig",
    "DNSTunnelState",
    # Encoder
    "DNSEncoder",
    "Base32Encoder",
    "Base64Encoder",
    # Client
    "DNSClient",
    "DNSRecord",
    "DNSQuery",
]

