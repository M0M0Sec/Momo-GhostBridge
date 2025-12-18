"""
Tests for the main GhostBridge application.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from ghostbridge.main import GhostBridge, GhostBridgeStatus
from ghostbridge.core.config import GhostBridgeConfig


@pytest.fixture
def config():
    """Create test configuration."""
    return GhostBridgeConfig()


@pytest.fixture
def ghostbridge(config):
    """Create GhostBridge instance."""
    with patch("ghostbridge.main.BridgeManager"), \
         patch("ghostbridge.main.TunnelManager"), \
         patch("ghostbridge.main.StealthManager"):
        return GhostBridge(config=config)


class TestGhostBridgeInit:
    """Test GhostBridge initialization."""

    def test_create_with_config(self, config):
        """Test creating GhostBridge with config."""
        with patch("ghostbridge.main.BridgeManager"), \
             patch("ghostbridge.main.TunnelManager"), \
             patch("ghostbridge.main.StealthManager"):
            ghost = GhostBridge(config=config)
            assert ghost.config == config

    def test_uptime_starts_at_zero(self, ghostbridge):
        """Test uptime starts near zero."""
        assert ghostbridge.uptime < 1.0


class TestGhostBridgeStart:
    """Test GhostBridge start functionality."""

    @pytest.mark.asyncio
    async def test_start_success(self, ghostbridge):
        """Test successful start."""
        ghostbridge._bridge.setup = AsyncMock(return_value=True)
        ghostbridge._tunnel.connect = AsyncMock(return_value=True)
        ghostbridge._tunnel.start_auto_reconnect = AsyncMock()
        ghostbridge._tunnel.start_monitoring = AsyncMock()
        ghostbridge._stealth.setup_ram_logging = AsyncMock()
        ghostbridge._stealth.suppress_logs = AsyncMock()
        ghostbridge._stealth.start_monitoring = AsyncMock()

        result = await ghostbridge.start()
        assert result is True

    @pytest.mark.asyncio
    async def test_start_bridge_failure(self, ghostbridge):
        """Test start fails when bridge setup fails."""
        ghostbridge._bridge.setup = AsyncMock(return_value=False)
        ghostbridge._stealth.setup_ram_logging = AsyncMock()
        ghostbridge._stealth.suppress_logs = AsyncMock()
        ghostbridge._stealth.start_monitoring = AsyncMock()

        result = await ghostbridge.start()
        assert result is False


class TestGhostBridgeStop:
    """Test GhostBridge stop functionality."""

    @pytest.mark.asyncio
    async def test_stop(self, ghostbridge):
        """Test stopping GhostBridge."""
        ghostbridge._tunnel.disconnect = AsyncMock()
        ghostbridge._bridge.teardown = AsyncMock()
        ghostbridge._stealth.stop_monitoring = AsyncMock()
        ghostbridge._stealth.suppress_logs = AsyncMock()

        await ghostbridge.stop()

        ghostbridge._tunnel.disconnect.assert_called_once()
        ghostbridge._bridge.teardown.assert_called_once()


class TestGhostBridgeHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, ghostbridge):
        """Test health check when all components healthy."""
        ghostbridge._bridge.get_status = AsyncMock(
            return_value=MagicMock(is_active=True)
        )
        ghostbridge._tunnel.get_status = AsyncMock(
            return_value=MagicMock(is_connected=True)
        )
        ghostbridge._beacon = MagicMock(is_running=True)

        result = await ghostbridge.health_check()

        assert result["healthy"] is True
        assert result["components"]["bridge"] is True
        assert result["components"]["tunnel"] is True
        assert result["components"]["beacon"] is True

    @pytest.mark.asyncio
    async def test_health_check_tunnel_disconnected(self, ghostbridge):
        """Test health check when tunnel disconnected."""
        ghostbridge._bridge.get_status = AsyncMock(
            return_value=MagicMock(is_active=True)
        )
        ghostbridge._tunnel.get_status = AsyncMock(
            return_value=MagicMock(is_connected=False)
        )

        result = await ghostbridge.health_check()

        assert result["healthy"] is False
        assert result["components"]["tunnel"] is False


class TestGhostBridgeStatus:
    """Test status functionality."""

    @pytest.mark.asyncio
    async def test_get_status(self, ghostbridge, config):
        """Test getting full status."""
        ghostbridge._bridge.is_active = True
        ghostbridge._bridge.target_mac = "00:11:22:33:44:55"
        ghostbridge._tunnel.is_connected = True
        ghostbridge._tunnel.state = MagicMock(value="connected")
        ghostbridge._stealth.level = MagicMock(value="normal")
        ghostbridge._beacon = MagicMock(
            is_running=True,
            stats=MagicMock(last_success_time=datetime.now())
        )

        status = await ghostbridge.get_status()

        assert status.device_id == config.device.id
        assert status.bridge_active is True
        assert status.tunnel_connected is True


class TestGhostBridgePanic:
    """Test panic callback."""

    def test_panic_sets_shutdown(self, ghostbridge):
        """Test panic callback sets shutdown event."""
        assert not ghostbridge._shutdown_event.is_set()
        
        ghostbridge._on_panic()
        
        assert ghostbridge._shutdown_event.is_set()

