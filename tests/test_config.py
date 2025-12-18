"""
Tests for GhostBridge Configuration Module
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from ghostbridge.core.config import (
    BeaconConfig,
    C2Config,
    DeviceConfig,
    GhostBridgeConfig,
    LoggingConfig,
    NetworkConfig,
    StealthConfig,
    TunnelConfig,
)


class TestDeviceConfig:
    """Tests for DeviceConfig."""

    def test_default_values(self):
        """Test default device configuration."""
        config = DeviceConfig()
        assert config.id == "ghost-001"
        assert config.name == "GhostBridge Device"

    def test_custom_values(self):
        """Test custom device configuration."""
        config = DeviceConfig(id="ghost-test", name="Test Device")
        assert config.id == "ghost-test"
        assert config.name == "Test Device"


class TestNetworkConfig:
    """Tests for NetworkConfig."""

    def test_default_values(self):
        """Test default network configuration."""
        config = NetworkConfig()
        assert config.bridge_name == "br0"
        assert config.wan_interface == "eth0"
        assert config.lan_interface == "eth1"
        assert config.clone_mac is True

    def test_interface_name_validation(self):
        """Test interface name validation."""
        # Valid names
        NetworkConfig(bridge_name="br0")
        NetworkConfig(wan_interface="eth-0")
        NetworkConfig(lan_interface="ens_p0")

        # Invalid names
        with pytest.raises(ValueError):
            NetworkConfig(bridge_name="")  # Empty

        with pytest.raises(ValueError):
            NetworkConfig(bridge_name="a" * 20)  # Too long


class TestTunnelConfig:
    """Tests for TunnelConfig."""

    def test_default_values(self):
        """Test default tunnel configuration."""
        config = TunnelConfig()
        assert config.type == "wireguard"
        assert config.interface == "wg0"
        assert config.keepalive == 25
        assert config.reconnect_delays == [5, 10, 30, 60, 300]

    def test_tunnel_type_validation(self):
        """Test tunnel type validation."""
        # Valid types
        TunnelConfig(type="wireguard")
        TunnelConfig(type="openvpn")
        TunnelConfig(type="ssh")
        TunnelConfig(type="cloudflare")

        # Invalid type
        with pytest.raises(ValueError):
            TunnelConfig(type="invalid")

    def test_keepalive_bounds(self):
        """Test keepalive value bounds."""
        TunnelConfig(keepalive=0)
        TunnelConfig(keepalive=300)

        with pytest.raises(ValueError):
            TunnelConfig(keepalive=-1)

        with pytest.raises(ValueError):
            TunnelConfig(keepalive=301)


class TestBeaconConfig:
    """Tests for BeaconConfig."""

    def test_default_values(self):
        """Test default beacon configuration."""
        config = BeaconConfig()
        assert config.enabled is True
        assert config.interval == 300
        assert config.jitter == 60

    def test_interval_bounds(self):
        """Test interval value bounds."""
        BeaconConfig(interval=10)
        BeaconConfig(interval=86400)

        with pytest.raises(ValueError):
            BeaconConfig(interval=5)

        with pytest.raises(ValueError):
            BeaconConfig(interval=86401)


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

        # Case insensitive
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"

        # Invalid level
        with pytest.raises(ValueError):
            LoggingConfig(level="TRACE")


class TestGhostBridgeConfig:
    """Tests for main GhostBridgeConfig."""

    def test_default_config(self):
        """Test default configuration loading."""
        config = GhostBridgeConfig()

        assert isinstance(config.device, DeviceConfig)
        assert isinstance(config.network, NetworkConfig)
        assert isinstance(config.tunnel, TunnelConfig)
        assert isinstance(config.beacon, BeaconConfig)
        assert isinstance(config.c2, C2Config)
        assert isinstance(config.stealth, StealthConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_yaml_round_trip(self):
        """Test saving and loading from YAML."""
        config = GhostBridgeConfig(
            device=DeviceConfig(id="test-device", name="Test"),
            network=NetworkConfig(bridge_name="br_test"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yml"
            config.to_yaml(yaml_path)

            loaded = GhostBridgeConfig.from_yaml(yaml_path)

            assert loaded.device.id == "test-device"
            assert loaded.device.name == "Test"
            assert loaded.network.bridge_name == "br_test"

    def test_from_yaml_file_not_found(self):
        """Test error when YAML file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            GhostBridgeConfig.from_yaml("/nonexistent/path/config.yml")

    def test_get_bridge_interfaces(self):
        """Test getting bridge interface tuple."""
        config = GhostBridgeConfig(
            network=NetworkConfig(
                bridge_name="br_test",
                wan_interface="wan0",
                lan_interface="lan0",
            )
        )

        bridge, wan, lan = config.get_bridge_interfaces()
        assert bridge == "br_test"
        assert wan == "wan0"
        assert lan == "lan0"

    def test_nested_config_from_dict(self):
        """Test creating config from nested dictionary."""
        data = {
            "device": {"id": "ghost-nested", "name": "Nested Test"},
            "network": {"bridge_name": "br_nested", "clone_mac": False},
            "beacon": {"interval": 600},
        }

        config = GhostBridgeConfig(**data)

        assert config.device.id == "ghost-nested"
        assert config.network.bridge_name == "br_nested"
        assert config.network.clone_mac is False
        assert config.beacon.interval == 600

    def test_yaml_content_structure(self):
        """Test YAML output structure."""
        config = GhostBridgeConfig()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yml"
            config.to_yaml(yaml_path)

            with open(yaml_path) as f:
                data = yaml.safe_load(f)

            # Check top-level keys
            assert "device" in data
            assert "network" in data
            assert "tunnel" in data
            assert "beacon" in data
            assert "c2" in data
            assert "stealth" in data
            assert "logging" in data

