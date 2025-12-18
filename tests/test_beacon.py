"""
Tests for Beacon Service
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghostbridge.c2.beacon import BeaconService, BeaconStats
from ghostbridge.c2.client import Command, CommandResponse, MoMoClient
from ghostbridge.core.config import GhostBridgeConfig


class TestBeaconStats:
    """Tests for BeaconStats."""

    def test_initial_values(self):
        """Test initial statistics values."""
        stats = BeaconStats()

        assert stats.total_beacons == 0
        assert stats.successful_beacons == 0
        assert stats.failed_beacons == 0
        assert stats.last_beacon_time is None


class TestBeaconService:
    """Tests for BeaconService."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GhostBridgeConfig()

    @pytest.fixture
    def mock_client(self):
        """Create mock MoMo client."""
        client = MagicMock(spec=MoMoClient)
        client.beacon = AsyncMock(return_value={"commands": []})
        client.send_response = AsyncMock(return_value={})
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def beacon(self, config, mock_client):
        """Create beacon service with mock client."""
        service = BeaconService(config, client=mock_client)
        return service

    def test_initialization(self, config):
        """Test service initialization."""
        service = BeaconService(config)

        assert service.config == config
        assert not service.is_running

    def test_initial_stats(self, beacon):
        """Test initial statistics."""
        stats = beacon.stats

        assert stats.total_beacons == 0
        assert stats.successful_beacons == 0
        assert stats.failed_beacons == 0

    def test_register_handler(self, beacon):
        """Test custom handler registration."""
        def custom_handler(cmd):
            return CommandResponse(cmd.id, "success", "custom")

        beacon.register_handler("custom", custom_handler)

        assert "custom" in beacon._handlers

    @pytest.mark.asyncio
    async def test_send_beacon_success(self, beacon, mock_client):
        """Test successful beacon."""
        result = await beacon._send_beacon()

        assert result is True
        assert beacon.stats.total_beacons == 1
        assert beacon.stats.successful_beacons == 1
        assert beacon.stats.failed_beacons == 0
        mock_client.beacon.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_beacon_failure(self, beacon, mock_client):
        """Test failed beacon."""
        from ghostbridge.c2.client import MoMoClientError

        mock_client.beacon = AsyncMock(side_effect=MoMoClientError("Connection failed"))

        result = await beacon._send_beacon()

        assert result is False
        assert beacon.stats.total_beacons == 1
        assert beacon.stats.successful_beacons == 0
        assert beacon.stats.failed_beacons == 1
        assert beacon.stats.last_error is not None

    @pytest.mark.asyncio
    async def test_process_commands(self, beacon, mock_client):
        """Test command processing from beacon response."""
        commands = [
            {
                "command_id": "cmd-1",
                "action": "ping",
                "payload": {},
            }
        ]

        await beacon._process_commands(commands)

        assert beacon.stats.commands_received == 1
        assert beacon.stats.commands_executed == 1
        mock_client.send_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_unknown_command(self, beacon, mock_client):
        """Test processing unknown command."""
        commands = [
            {
                "command_id": "cmd-1",
                "action": "unknown_action",
                "payload": {},
            }
        ]

        await beacon._process_commands(commands)

        assert beacon.stats.commands_received == 1
        assert beacon.stats.commands_executed == 0

        # Should still send error response
        mock_client.send_response.assert_called_once()
        response = mock_client.send_response.call_args[0][0]
        assert response.status == "error"

    def test_get_jittered_interval(self, beacon):
        """Test jittered interval calculation."""
        intervals = [beacon._get_jittered_interval() for _ in range(100)]

        # Should have variation
        assert len(set(intervals)) > 1

        # Should be within expected range
        base = beacon._beacon_config.interval
        jitter = beacon._beacon_config.jitter
        assert all(base - jitter <= i <= base + jitter for i in intervals)

    @pytest.mark.asyncio
    async def test_start_stop(self, beacon):
        """Test starting and stopping service."""
        assert not beacon.is_running

        await beacon.start()
        assert beacon.is_running

        # Let it run briefly
        await asyncio.sleep(0.1)

        await beacon.stop()
        assert not beacon.is_running

    @pytest.mark.asyncio
    async def test_force_beacon(self, beacon, mock_client):
        """Test forced beacon."""
        result = await beacon.force_beacon()

        assert result is True
        assert beacon.stats.total_beacons == 1

    def test_default_handlers_registered(self, beacon):
        """Test default handlers are registered."""
        assert "status" in beacon._handlers
        assert "ping" in beacon._handlers
        assert "shell" in beacon._handlers
        assert "config" in beacon._handlers

    def test_handle_ping(self, beacon):
        """Test ping command handler."""
        from datetime import datetime

        cmd = Command(
            id="test-cmd",
            action="ping",
            payload={},
            timestamp=datetime.now(),
        )

        handler = beacon._handlers["ping"]
        response = handler(cmd)

        assert response.status == "success"
        assert response.result == "pong"

    def test_handle_status(self, beacon):
        """Test status command handler."""
        from datetime import datetime

        cmd = Command(
            id="test-cmd",
            action="status",
            payload={},
            timestamp=datetime.now(),
        )

        handler = beacon._handlers["status"]
        response = handler(cmd)

        assert response.status == "success"
        assert "device_id" in response.result
        assert "uptime" in response.result

