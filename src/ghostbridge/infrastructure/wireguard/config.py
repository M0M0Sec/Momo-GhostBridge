"""
WireGuard Configuration Generator

Generates and manages WireGuard configuration files.
"""

from __future__ import annotations

import secrets
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WireGuardPeer:
    """WireGuard peer configuration."""

    public_key: str
    endpoint: str  # host:port
    allowed_ips: list[str] = field(default_factory=lambda: ["0.0.0.0/0"])
    persistent_keepalive: int = 25
    preshared_key: str | None = None

    def to_config(self) -> str:
        """Generate peer configuration block."""
        lines = [
            "[Peer]",
            f"PublicKey = {self.public_key}",
            f"Endpoint = {self.endpoint}",
            f"AllowedIPs = {', '.join(self.allowed_ips)}",
        ]

        if self.persistent_keepalive > 0:
            lines.append(f"PersistentKeepalive = {self.persistent_keepalive}")

        if self.preshared_key:
            lines.append(f"PresharedKey = {self.preshared_key}")

        return "\n".join(lines)


@dataclass
class WireGuardConfig:
    """WireGuard interface configuration."""

    interface: str = "wg0"
    private_key: str = ""
    address: str = "10.66.66.2/24"
    listen_port: int | None = None
    dns: str | None = None
    mtu: int = 1420
    peers: list[WireGuardPeer] = field(default_factory=list)

    # File paths
    config_dir: Path = field(default_factory=lambda: Path("/etc/wireguard"))

    def __post_init__(self) -> None:
        """Generate private key if not provided."""
        if not self.private_key:
            self.private_key = self.generate_private_key()

    @staticmethod
    def generate_private_key() -> str:
        """
        Generate a WireGuard private key.

        Returns:
            Base64-encoded private key
        """
        try:
            result = subprocess.run(
                ["wg", "genkey"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: generate random bytes (not cryptographically ideal but works)
            import base64
            return base64.b64encode(secrets.token_bytes(32)).decode()

    @staticmethod
    def derive_public_key(private_key: str) -> str:
        """
        Derive public key from private key.

        Args:
            private_key: WireGuard private key

        Returns:
            Base64-encoded public key
        """
        try:
            result = subprocess.run(
                ["wg", "pubkey"],
                input=private_key,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("WireGuard tools not available")

    @property
    def public_key(self) -> str:
        """Get public key derived from private key."""
        return self.derive_public_key(self.private_key)

    @property
    def config_path(self) -> Path:
        """Get path to WireGuard config file."""
        return self.config_dir / f"{self.interface}.conf"

    def add_peer(
        self,
        public_key: str,
        endpoint: str,
        allowed_ips: list[str] | None = None,
        keepalive: int = 25,
    ) -> None:
        """
        Add a peer to the configuration.

        Args:
            public_key: Peer's public key
            endpoint: Peer's endpoint (host:port)
            allowed_ips: Allowed IP ranges
            keepalive: Keepalive interval in seconds
        """
        peer = WireGuardPeer(
            public_key=public_key,
            endpoint=endpoint,
            allowed_ips=allowed_ips or ["10.66.66.0/24"],
            persistent_keepalive=keepalive,
        )
        self.peers.append(peer)

    def to_config(self) -> str:
        """
        Generate complete WireGuard configuration.

        Returns:
            Configuration file contents
        """
        lines = [
            "[Interface]",
            f"PrivateKey = {self.private_key}",
            f"Address = {self.address}",
        ]

        if self.listen_port:
            lines.append(f"ListenPort = {self.listen_port}")

        if self.dns:
            lines.append(f"DNS = {self.dns}")

        if self.mtu != 1420:
            lines.append(f"MTU = {self.mtu}")

        # Add peers
        for peer in self.peers:
            lines.append("")
            lines.append(peer.to_config())

        return "\n".join(lines)

    def save(self, path: Path | None = None) -> Path:
        """
        Save configuration to file.

        Args:
            path: Optional custom path

        Returns:
            Path to saved file
        """
        save_path = path or self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with restricted permissions
        save_path.write_text(self.to_config())
        save_path.chmod(0o600)

        return save_path

    @classmethod
    def from_file(cls, path: Path) -> WireGuardConfig:
        """
        Load configuration from file.

        Args:
            path: Path to config file

        Returns:
            WireGuardConfig instance
        """
        content = path.read_text()
        return cls.parse(content, interface=path.stem)

    @classmethod
    def parse(cls, content: str, interface: str = "wg0") -> WireGuardConfig:
        """
        Parse WireGuard configuration content.

        Args:
            content: Configuration file content
            interface: Interface name

        Returns:
            WireGuardConfig instance
        """
        config = cls(interface=interface)
        current_section = None
        current_peer: dict = {}

        for line in content.split("\n"):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if line == "[Interface]":
                current_section = "interface"
                continue
            elif line == "[Peer]":
                if current_peer:
                    config.peers.append(WireGuardPeer(**current_peer))
                current_section = "peer"
                current_peer = {}
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()

            if current_section == "interface":
                if key == "privatekey":
                    config.private_key = value
                elif key == "address":
                    config.address = value
                elif key == "listenport":
                    config.listen_port = int(value)
                elif key == "dns":
                    config.dns = value
                elif key == "mtu":
                    config.mtu = int(value)

            elif current_section == "peer":
                if key == "publickey":
                    current_peer["public_key"] = value
                elif key == "endpoint":
                    current_peer["endpoint"] = value
                elif key == "allowedips":
                    current_peer["allowed_ips"] = [ip.strip() for ip in value.split(",")]
                elif key == "persistentkeepalive":
                    current_peer["persistent_keepalive"] = int(value)
                elif key == "presharedkey":
                    current_peer["preshared_key"] = value

        # Add last peer
        if current_peer:
            config.peers.append(WireGuardPeer(**current_peer))

        return config

