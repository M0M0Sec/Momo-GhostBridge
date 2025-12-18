"""
Tests for Tunnel Module
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghostbridge.core.config import GhostBridgeConfig
from ghostbridge.core.tunnel import (
    ConnectionState,
    ConnectionStats,
    ReconnectPolicy,
    TunnelManager,
)


class TestReconnectPolicy:
    """Tests for ReconnectPolicy."""

    def test_default_delays(self):
        """Test default delay sequence."""
        policy = ReconnectPolicy()
        assert policy.delays == [5, 10, 30, 60, 300]

    def test_get_delay_within_range(self):
        """Test delay retrieval within range."""
        policy = ReconnectPolicy(delays=[10, 20, 30], jitter_percent=0)

        assert policy.get_delay(0) == 10
        assert policy.get_delay(1) == 20
        assert policy.get_delay(2) == 30

    def test_get_delay_beyond_range(self):
        """Test delay retrieval beyond range (uses last value)."""
        policy = ReconnectPolicy(delays=[10, 20, 30], jitter_percent=0)

        assert policy.get_delay(5) == 30
        assert policy.get_delay(100) == 30

    def test_get_delay_with_jitter(self):
        """Test delay includes jitter."""
        policy = ReconnectPolicy(delays=[100], jitter_percent=0.2)

        delays = [policy.get_delay(0) for _ in range(100)]

        # Should have some variation
        assert min(delays) < 100
        assert max(delays) > 100
        # But within ±20%
        assert all(80 <= d <= 120 for d in delays)

    def test_should_retry_unlimited(self):
        """Test unlimited retries (max_attempts=0)."""
        policy = ReconnectPolicy(max_attempts=0)

        assert policy.should_retry(0) is True
        assert policy.should_retry(100) is True
        assert policy.should_retry(10000) is True

    def test_should_retry_limited(self):
        """Test limited retries."""
        policy = ReconnectPolicy(max_attempts=3)

        assert policy.should_retry(0) is True
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False
        assert policy.should_retry(10) is False


class TestConnectionStats:
    """Tests for ConnectionStats."""

    def test_uptime_no_connection(self):
        """Test uptime with no connection."""
        stats = ConnectionStats()
        assert stats.uptime_seconds == 0.0

    def test_uptime_with_connection(self):
        """Test uptime calculation."""
        from datetime import datetime, timedelta

        stats = ConnectionStats()
        stats.connect_time = datetime.now() - timedelta(seconds=100)

        uptime = stats.uptime_seconds
        assert 99 <= uptime <= 101


class TestTunnelManager:
    """Tests for TunnelManager."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GhostBridgeConfig()

    @pytest.fixture
    def tunnel_manager(self, config):
        """Create tunnel manager with mocked WireGuard."""
        with patch("ghostbridge.core.tunnel.WireGuardManager") as MockWG:
            mock_wg = MagicMock()
            MockWG.return_value = mock_wg
            
            manager = TunnelManager(config)
            manager._wireguard = mock_wg
            return manager

    def test_initialization(self, config):
        """Test tunnel manager initialization."""
        with patch("ghostbridge.core.tunnel.WireGuardManager"):
            manager = TunnelManager(config)
            
            assert manager.state == ConnectionState.IDLE
            assert not manager.is_connected

    def test_initial_stats(self, tunnel_manager):
        """Test initial statistics."""
        stats = tunnel_manager.stats

        assert stats.total_connects == 0
        assert stats.total_disconnects == 0
        assert stats.reconnect_attempts == 0

    @pytest.mark.asyncio
    async def test_connect_success(self, tunnel_manager):
        """Test successful connection."""
        tunnel_manager._wireguard.up = AsyncMock(return_value=True)
        tunnel_manager._wait_for_handshake = AsyncMock(return_value=True)

        result = await tunnel_manager.connect()

        assert result is True
        assert tunnel_manager.state == ConnectionState.CONNECTED
        assert tunnel_manager.stats.total_connects == 1

    @pytest.mark.asyncio
    async def test_connect_failure(self, tunnel_manager):
        """Test connection failure."""
        tunnel_manager._wireguard.up = AsyncMock(return_value=False)

        result = await tunnel_manager.connect()

        assert result is False
        assert tunnel_manager.state == ConnectionState.FAILED

    @pytest.mark.asyncio
    async def test_disconnect(self, tunnel_manager):
        """Test disconnection."""
        tunnel_manager._wireguard.down = AsyncMock(return_value=True)

        result = await tunnel_manager.disconnect()

        assert result is True
        assert tunnel_manager.state == ConnectionState.DISCONNECTED
        assert tunnel_manager.stats.total_disconnects == 1

    def test_state_change_callback(self, tunnel_manager):
        """Test state change callback."""
        callback = MagicMock()
        tunnel_manager.on_state_change(callback)

        tunnel_manager._set_state(ConnectionState.CONNECTING)

        callback.assert_called_once_with(ConnectionState.CONNECTING)

    def test_is_connected_property(self, tunnel_manager):
        """Test is_connected property."""
        assert not tunnel_manager.is_connected

        tunnel_manager._state = ConnectionState.CONNECTED
        assert tunnel_manager.is_connected

        tunnel_manager._state = ConnectionState.RECONNECTING
        assert not tunnel_manager.is_connected

    def test_request_shutdown(self, tunnel_manager):
        """Test shutdown request."""
        assert not tunnel_manager._shutdown_event.is_set()

        tunnel_manager.request_shutdown()

        assert tunnel_manager._shutdown_event.is_set()

