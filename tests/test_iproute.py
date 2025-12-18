"""
Tests for IPRoute wrapper

Note: These tests mock the subprocess calls since we can't run
actual iproute2 commands in the test environment.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghostbridge.infrastructure.network.iproute import (
    IPRoute,
    IPRouteError,
    InterfaceInfo,
    InterfaceState,
)


class TestInterfaceInfo:
    """Tests for InterfaceInfo dataclass."""

    def test_is_up(self):
        """Test is_up property."""
        info = InterfaceInfo(
            name="eth0",
            mac_address="aa:bb:cc:dd:ee:ff",
            state=InterfaceState.UP,
            mtu=1500,
        )
        assert info.is_up is True

        info = InterfaceInfo(
            name="eth0",
            mac_address="aa:bb:cc:dd:ee:ff",
            state=InterfaceState.DOWN,
            mtu=1500,
        )
        assert info.is_up is False

    def test_is_bridge_member(self):
        """Test is_bridge_member property."""
        info = InterfaceInfo(
            name="eth0",
            mac_address="aa:bb:cc:dd:ee:ff",
            state=InterfaceState.UP,
            mtu=1500,
            master="br0",
        )
        assert info.is_bridge_member is True

        info = InterfaceInfo(
            name="eth0",
            mac_address="aa:bb:cc:dd:ee:ff",
            state=InterfaceState.UP,
            mtu=1500,
            master=None,
        )
        assert info.is_bridge_member is False


class TestIPRouteError:
    """Tests for IPRouteError exception."""

    def test_error_message(self):
        """Test error message formatting."""
        error = IPRouteError("ip link show eth0", 1, "Device not found")
        assert "ip link show eth0" in str(error)
        assert "failed with code 1" in str(error)
        assert "Device not found" in str(error)


class TestIPRoute:
    """Tests for IPRoute wrapper."""

    @pytest.fixture
    def iproute(self):
        """Create IPRoute instance without sudo."""
        return IPRoute(sudo=False)

    @pytest.fixture
    def mock_process(self):
        """Create mock subprocess."""
        process = AsyncMock()
        process.returncode = 0
        process.communicate = AsyncMock(return_value=(b"", b""))
        return process

    @pytest.mark.asyncio
    async def test_run_success(self, iproute, mock_process):
        """Test successful command execution."""
        mock_process.communicate.return_value = (b"output", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            stdout, stderr, code = await iproute._run("ip", "link", "show")

            assert stdout == "output"
            assert stderr == ""
            assert code == 0

    @pytest.mark.asyncio
    async def test_run_failure(self, iproute, mock_process):
        """Test command failure."""
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"error message")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(IPRouteError) as exc_info:
                await iproute._run("ip", "link", "show", "eth99")

            assert exc_info.value.returncode == 1
            assert "error message" in exc_info.value.stderr

    @pytest.mark.asyncio
    async def test_interface_exists_true(self, iproute, mock_process):
        """Test interface exists check - true case."""
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await iproute.interface_exists("eth0")
            assert result is True

    @pytest.mark.asyncio
    async def test_interface_exists_false(self, iproute, mock_process):
        """Test interface exists check - false case."""
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Device not found")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await iproute.interface_exists("eth99")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_interface_info(self, iproute, mock_process):
        """Test getting interface information."""
        output = b"2: eth0: <BROADCAST,MULTICAST,UP> mtu 1500 master br0 link/ether aa:bb:cc:dd:ee:ff"
        mock_process.communicate.return_value = (output, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            info = await iproute.get_interface_info("eth0")

            assert info.name == "eth0"
            assert info.mac_address == "aa:bb:cc:dd:ee:ff"
            assert info.state == InterfaceState.UP
            assert info.mtu == 1500
            assert info.master == "br0"

    def test_mac_pattern_valid(self, iproute):
        """Test MAC address pattern matching - valid."""
        assert iproute.MAC_PATTERN.match("aa:bb:cc:dd:ee:ff")
        assert iproute.MAC_PATTERN.match("AA:BB:CC:DD:EE:FF")
        assert iproute.MAC_PATTERN.match("00:11:22:33:44:55")

    def test_mac_pattern_invalid(self, iproute):
        """Test MAC address pattern matching - invalid."""
        assert not iproute.MAC_PATTERN.match("invalid")
        assert not iproute.MAC_PATTERN.match("aa:bb:cc:dd:ee")  # Too short
        assert not iproute.MAC_PATTERN.match("aa:bb:cc:dd:ee:ff:00")  # Too long
        assert not iproute.MAC_PATTERN.match("gg:bb:cc:dd:ee:ff")  # Invalid hex

    @pytest.mark.asyncio
    async def test_set_mac_address_validation(self, iproute):
        """Test MAC address validation in set_mac_address."""
        with pytest.raises(ValueError):
            await iproute.set_mac_address("eth0", "invalid-mac")

    @pytest.mark.asyncio
    async def test_get_arp_table(self, iproute, mock_process):
        """Test parsing ARP table."""
        output = b"""192.168.1.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
192.168.1.2 dev eth0 lladdr 11:22:33:44:55:66 STALE"""
        mock_process.communicate.return_value = (output, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            entries = await iproute.get_arp_table()

            assert len(entries) == 2
            assert entries[0]["ip"] == "192.168.1.1"
            assert entries[0]["mac"] == "aa:bb:cc:dd:ee:ff"
            assert entries[0]["state"] == "REACHABLE"
            assert entries[1]["ip"] == "192.168.1.2"
            assert entries[1]["state"] == "STALE"

    @pytest.mark.asyncio
    async def test_get_bridge_members(self, iproute, mock_process):
        """Test getting bridge members."""
        output = b"""3: eth0: <BROADCAST,MULTICAST,UP> master br0
4: eth1: <BROADCAST,MULTICAST,UP> master br0"""
        mock_process.communicate.return_value = (output, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            members = await iproute.get_bridge_members("br0")

            assert len(members) == 2
            assert "eth0" in members
            assert "eth1" in members

    def test_sudo_prefix(self):
        """Test sudo prefix configuration."""
        iproute_sudo = IPRoute(sudo=True)
        assert iproute_sudo._sudo_prefix == ["sudo"]

        iproute_no_sudo = IPRoute(sudo=False)
        assert iproute_no_sudo._sudo_prefix == []

