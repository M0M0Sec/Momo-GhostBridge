"""
Tests for GhostBridge Bridge Module
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghostbridge.core.bridge import BridgeManager, BridgeMode
from ghostbridge.core.config import GhostBridgeConfig
from ghostbridge.infrastructure.network.manager import NetworkState


class TestBridgeManager:
    """Tests for BridgeManager."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GhostBridgeConfig()

    @pytest.fixture
    def bridge(self, config):
        """Create bridge manager with mocked network."""
        with patch("ghostbridge.core.bridge.NetworkManager") as MockNetwork:
            mock_network = MagicMock()
            mock_network.state = NetworkState.UNCONFIGURED
            mock_network.target_mac = None
            MockNetwork.return_value = mock_network
            
            manager = BridgeManager(config=config)
            manager._network = mock_network
            return manager

    def test_initialization(self, config):
        """Test bridge manager initialization."""
        with patch("ghostbridge.core.bridge.NetworkManager"):
            manager = BridgeManager(config=config)
            
            assert manager.config == config
            assert manager.mode == BridgeMode.TRANSPARENT
            assert not manager.is_active
            assert manager.uptime == 0.0

    def test_initialization_with_mode(self, config):
        """Test bridge manager with custom mode."""
        with patch("ghostbridge.core.bridge.NetworkManager"):
            manager = BridgeManager(config=config, mode=BridgeMode.MONITOR)
            assert manager.mode == BridgeMode.MONITOR

    @pytest.mark.asyncio
    async def test_setup_success(self, bridge):
        """Test successful bridge setup."""
        bridge._network.setup_bridge = AsyncMock(return_value=True)
        bridge._network.start_monitoring = AsyncMock()
        bridge._network.state = NetworkState.ACTIVE

        result = await bridge.setup()

        assert result is True
        bridge._network.setup_bridge.assert_called_once()
        bridge._network.start_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_failure(self, bridge):
        """Test failed bridge setup."""
        bridge._network.setup_bridge = AsyncMock(return_value=False)

        result = await bridge.setup()

        assert result is False
        assert bridge._start_time is None

    @pytest.mark.asyncio
    async def test_teardown(self, bridge):
        """Test bridge teardown."""
        bridge._network.stop_monitoring = AsyncMock()
        bridge._network.teardown_bridge = AsyncMock(return_value=True)

        result = await bridge.teardown()

        assert result is True
        bridge._network.stop_monitoring.assert_called_once()
        bridge._network.teardown_bridge.assert_called_once()

    def test_state_property(self, bridge):
        """Test state property."""
        bridge._network.state = NetworkState.ACTIVE
        assert bridge.state == NetworkState.ACTIVE

        bridge._network.state = NetworkState.ERROR
        assert bridge.state == NetworkState.ERROR

    def test_target_mac_property(self, bridge):
        """Test target_mac property."""
        bridge._network.target_mac = "aa:bb:cc:dd:ee:ff"
        assert bridge.target_mac == "aa:bb:cc:dd:ee:ff"

    def test_is_active(self, bridge):
        """Test is_active property."""
        bridge._network.state = NetworkState.UNCONFIGURED
        assert not bridge.is_active

        bridge._network.state = NetworkState.ACTIVE
        assert bridge.is_active

    def test_request_shutdown(self, bridge):
        """Test shutdown request."""
        assert not bridge._shutdown_event.is_set()
        bridge.request_shutdown()
        assert bridge._shutdown_event.is_set()


class TestBridgeMode:
    """Tests for BridgeMode enum."""

    def test_mode_values(self):
        """Test bridge mode values."""
        assert BridgeMode.TRANSPARENT.value == "transparent"
        assert BridgeMode.MONITOR.value == "monitor"
        assert BridgeMode.INTERCEPT.value == "intercept"

    def test_mode_from_string(self):
        """Test creating mode from string."""
        assert BridgeMode("transparent") == BridgeMode.TRANSPARENT
        assert BridgeMode("monitor") == BridgeMode.MONITOR

