"""
Tests for WireGuard Module
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from ghostbridge.infrastructure.wireguard.config import WireGuardConfig, WireGuardPeer
from ghostbridge.infrastructure.wireguard.manager import (
    PeerStatus,
    TunnelState,
    TunnelStatus,
    WireGuardManager,
)


class TestWireGuardPeer:
    """Tests for WireGuardPeer."""

    def test_default_values(self):
        """Test default peer configuration."""
        peer = WireGuardPeer(
            public_key="test_key",
            endpoint="example.com:51820",
        )

        assert peer.public_key == "test_key"
        assert peer.endpoint == "example.com:51820"
        assert peer.allowed_ips == ["0.0.0.0/0"]
        assert peer.persistent_keepalive == 25

    def test_to_config(self):
        """Test peer config generation."""
        peer = WireGuardPeer(
            public_key="ABC123",
            endpoint="c2.example.com:51820",
            allowed_ips=["10.66.66.0/24"],
            persistent_keepalive=30,
        )

        config = peer.to_config()

        assert "[Peer]" in config
        assert "PublicKey = ABC123" in config
        assert "Endpoint = c2.example.com:51820" in config
        assert "AllowedIPs = 10.66.66.0/24" in config
        assert "PersistentKeepalive = 30" in config


class TestWireGuardConfig:
    """Tests for WireGuardConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WireGuardConfig()

        assert config.interface == "wg0"
        assert config.address == "10.66.66.2/24"
        assert config.mtu == 1420
        assert len(config.private_key) > 0  # Should be generated

    def test_add_peer(self):
        """Test adding peer."""
        config = WireGuardConfig()
        config.add_peer(
            public_key="server_pubkey",
            endpoint="c2.example.com:51820",
            allowed_ips=["10.66.66.0/24"],
            keepalive=25,
        )

        assert len(config.peers) == 1
        assert config.peers[0].public_key == "server_pubkey"

    def test_to_config(self):
        """Test config file generation."""
        config = WireGuardConfig(
            interface="wg0",
            private_key="test_private_key",
            address="10.66.66.2/24",
        )
        config.add_peer(
            public_key="server_pubkey",
            endpoint="c2.example.com:51820",
        )

        content = config.to_config()

        assert "[Interface]" in content
        assert "PrivateKey = test_private_key" in content
        assert "Address = 10.66.66.2/24" in content
        assert "[Peer]" in content
        assert "PublicKey = server_pubkey" in content

    def test_save_and_load(self, tmp_path):
        """Test saving and loading config."""
        config = WireGuardConfig(
            interface="wg_test",
            private_key="test_key_123",
            address="10.99.99.2/24",
            config_dir=tmp_path,
        )
        config.add_peer(
            public_key="peer_key",
            endpoint="test.com:51820",
        )

        # Save
        saved_path = config.save()
        assert saved_path.exists()
        assert saved_path.name == "wg_test.conf"

        # Load
        loaded = WireGuardConfig.from_file(saved_path)
        assert loaded.private_key == "test_key_123"
        assert loaded.address == "10.99.99.2/24"
        assert len(loaded.peers) == 1

    def test_parse_config(self):
        """Test parsing config content."""
        content = """[Interface]
PrivateKey = my_private_key
Address = 10.66.66.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = server_public_key
Endpoint = vpn.example.com:51820
AllowedIPs = 10.66.66.0/24
PersistentKeepalive = 25
"""
        config = WireGuardConfig.parse(content)

        assert config.private_key == "my_private_key"
        assert config.address == "10.66.66.2/24"
        assert config.dns == "1.1.1.1"
        assert len(config.peers) == 1
        assert config.peers[0].public_key == "server_public_key"
        assert config.peers[0].endpoint == "vpn.example.com:51820"


class TestPeerStatus:
    """Tests for PeerStatus."""

    def test_has_handshake(self):
        """Test handshake detection."""
        from datetime import datetime

        # No handshake
        peer = PeerStatus(
            public_key="key",
            endpoint="endpoint",
            allowed_ips=[],
            latest_handshake=None,
            transfer_rx=0,
            transfer_tx=0,
        )
        assert not peer.has_handshake

        # Has handshake
        peer = PeerStatus(
            public_key="key",
            endpoint="endpoint",
            allowed_ips=[],
            latest_handshake=datetime.now(),
            transfer_rx=0,
            transfer_tx=0,
        )
        assert peer.has_handshake

    def test_handshake_age(self):
        """Test handshake age calculation."""
        from datetime import datetime, timedelta

        peer = PeerStatus(
            public_key="key",
            endpoint="endpoint",
            allowed_ips=[],
            latest_handshake=datetime.now() - timedelta(seconds=60),
            transfer_rx=0,
            transfer_tx=0,
        )

        age = peer.handshake_age_seconds
        assert age is not None
        assert 59 <= age <= 61


class TestTunnelStatus:
    """Tests for TunnelStatus."""

    def test_is_connected_with_handshake(self):
        """Test is_connected with active handshake."""
        from datetime import datetime

        status = TunnelStatus(
            interface="wg0",
            state=TunnelState.CONNECTED,
            public_key="key",
            listen_port=51820,
            peers=[
                PeerStatus(
                    public_key="peer_key",
                    endpoint="endpoint",
                    allowed_ips=["10.66.66.0/24"],
                    latest_handshake=datetime.now(),
                    transfer_rx=1000,
                    transfer_tx=500,
                )
            ],
        )

        assert status.is_connected

    def test_is_connected_without_handshake(self):
        """Test is_connected without handshake."""
        status = TunnelStatus(
            interface="wg0",
            state=TunnelState.CONNECTED,
            public_key="key",
            listen_port=51820,
            peers=[
                PeerStatus(
                    public_key="peer_key",
                    endpoint="endpoint",
                    allowed_ips=[],
                    latest_handshake=None,
                    transfer_rx=0,
                    transfer_tx=0,
                )
            ],
        )

        assert not status.is_connected


class TestWireGuardManager:
    """Tests for WireGuardManager."""

    @pytest.fixture
    def wg_config(self):
        """Create test WireGuard config."""
        return WireGuardConfig(
            interface="wg_test",
            private_key="test_key",
        )

    @pytest.fixture
    def manager(self, wg_config):
        """Create WireGuard manager."""
        return WireGuardManager(wg_config, sudo=False)

    def test_initialization(self, wg_config):
        """Test manager initialization."""
        manager = WireGuardManager(wg_config)

        assert manager.interface == "wg_test"
        assert manager.state == TunnelState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_interface_exists_false(self, manager):
        """Test interface check when not exists."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"not found"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            exists = await manager.interface_exists()
            assert exists is False

    @pytest.mark.asyncio
    async def test_parse_wg_show(self, manager):
        """Test parsing wg show output."""
        output = """interface: wg0
  public key: device_public_key
  private key: (hidden)
  listening port: 51820

peer: peer_public_key
  endpoint: 1.2.3.4:51820
  allowed ips: 10.66.66.0/24
  latest handshake: 1 minute, 30 seconds ago
  transfer: 1.23 MiB received, 456 KiB sent
  persistent keepalive: every 25 seconds"""

        status = manager._parse_wg_show(output)

        assert status.public_key == "device_public_key"
        assert status.listen_port == 51820
        assert len(status.peers) == 1
        assert status.peers[0].public_key == "peer_public_key"
        assert status.peers[0].endpoint == "1.2.3.4:51820"
        assert status.peers[0].has_handshake
        assert status.peers[0].transfer_rx > 0
        assert status.peers[0].transfer_tx > 0

