"""
Tests for Stealth Module
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghostbridge.core.stealth import (
    StealthLevel,
    StealthManager,
    StealthStatus,
    ThreatLevel,
)


class TestStealthLevel:
    """Tests for StealthLevel enum."""

    def test_levels(self):
        """Test stealth level values."""
        assert StealthLevel.NORMAL.value == "normal"
        assert StealthLevel.ELEVATED.value == "elevated"
        assert StealthLevel.MAXIMUM.value == "maximum"
        assert StealthLevel.HIBERNATE.value == "hibernate"


class TestThreatLevel:
    """Tests for ThreatLevel enum."""

    def test_levels(self):
        """Test threat level values."""
        assert ThreatLevel.NONE.value == "none"
        assert ThreatLevel.LOW.value == "low"
        assert ThreatLevel.MEDIUM.value == "medium"
        assert ThreatLevel.HIGH.value == "high"
        assert ThreatLevel.CRITICAL.value == "critical"


class TestStealthManager:
    """Tests for StealthManager."""

    @pytest.fixture
    def manager(self):
        """Create stealth manager."""
        return StealthManager(
            ram_only=True,
            fake_identity="Netgear GS105",
            panic_on_tamper=False,  # Disable for testing
        )

    def test_initialization(self):
        """Test manager initialization."""
        manager = StealthManager()

        assert manager.ram_only is True
        assert manager.fake_identity == "Netgear GS105"
        assert manager.level == StealthLevel.NORMAL
        assert manager.threat_level == ThreatLevel.NONE

    def test_set_level(self, manager):
        """Test setting stealth level."""
        manager.set_level(StealthLevel.ELEVATED)
        assert manager.level == StealthLevel.ELEVATED

        manager.set_level(StealthLevel.MAXIMUM)
        assert manager.level == StealthLevel.MAXIMUM

    def test_get_status(self, manager):
        """Test getting status."""
        status = manager.get_status()

        assert isinstance(status, StealthStatus)
        assert status.level == StealthLevel.NORMAL
        assert status.threat_level == ThreatLevel.NONE
        assert status.ram_only is True

    def test_register_panic_callback(self, manager):
        """Test panic callback registration."""
        callback = MagicMock()
        manager.register_panic_callback(callback)

        assert callback in manager._panic_callbacks

    def test_get_fake_identity(self, manager):
        """Test fake identity generation."""
        identity = manager.get_fake_identity()

        assert identity["vendor"] == "NETGEAR"
        assert identity["model"] == "GS105v5"
        assert identity["type"] == "Unmanaged Switch"

    def test_get_fake_identity_custom(self):
        """Test custom fake identity."""
        manager = StealthManager(fake_identity="TP-Link TL-SG105")
        identity = manager.get_fake_identity()

        assert identity["vendor"] == "TP-LINK"
        assert identity["model"] == "TL-SG105"

    @pytest.mark.asyncio
    async def test_respond_to_probe_snmp(self, manager):
        """Test SNMP probe response."""
        response = await manager.respond_to_probe("snmp")

        assert response is not None
        assert b"NETGEAR" in response

    @pytest.mark.asyncio
    async def test_respond_to_probe_http(self, manager):
        """Test HTTP probe response (should be None)."""
        response = await manager.respond_to_probe("http")
        assert response is None

    @pytest.mark.asyncio
    async def test_respond_to_probe_banner(self, manager):
        """Test banner probe response."""
        response = await manager.respond_to_probe("banner")

        assert response is not None
        assert b"NETGEAR" in response

    def test_add_jitter(self):
        """Test jitter addition."""
        values = [StealthManager.add_jitter(100, 0.2) for _ in range(100)]

        # Should have variation
        assert len(set(values)) > 1

        # Should be within ±20%
        assert all(80 <= v <= 120 for v in values)

    @pytest.mark.asyncio
    async def test_random_delay(self, manager):
        """Test random delay."""
        import time

        start = time.monotonic()
        await manager.random_delay(0.1, 0.2)
        elapsed = time.monotonic() - start

        assert 0.1 <= elapsed <= 0.3

    @pytest.mark.asyncio
    async def test_suppress_logs_no_files(self, manager, tmp_path):
        """Test log suppression with no files."""
        # Patch paths to use temp directory
        with patch.object(manager, "SENSITIVE_PATHS", [str(tmp_path / "nonexistent")]):
            wiped = await manager.suppress_logs()
            assert wiped == 0

    @pytest.mark.asyncio
    async def test_suppress_logs_with_files(self, manager, tmp_path):
        """Test log suppression with files."""
        # Create test files
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "test.log").write_text("test log content")
        (log_dir / "test2.log").write_text("more content")

        with patch.object(manager, "SENSITIVE_PATHS", [str(log_dir)]):
            wiped = await manager.suppress_logs()
            assert wiped == 2

    @pytest.mark.asyncio
    async def test_secure_wipe_file(self, manager, tmp_path):
        """Test secure file wiping."""
        test_file = tmp_path / "secret.txt"
        test_file.write_text("sensitive data")

        success = await manager.secure_wipe_file(test_file, passes=1)

        assert success is True
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_secure_wipe_nonexistent(self, manager, tmp_path):
        """Test wiping nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"

        success = await manager.secure_wipe_file(test_file)
        assert success is True

    @pytest.mark.asyncio
    async def test_check_threats_clean(self, manager):
        """Test threat check with no threats."""
        with patch("subprocess.run") as mock_run:
            # Mock clean ps output
            mock_run.return_value = MagicMock(
                stdout="USER PID %CPU %MEM\nroot 1 0.0 0.1 /sbin/init",
                returncode=0,
            )

            level = await manager.check_threats()
            assert level == ThreatLevel.NONE


class TestStealthStatus:
    """Tests for StealthStatus dataclass."""

    def test_status_creation(self):
        """Test status creation."""
        from datetime import datetime

        status = StealthStatus(
            level=StealthLevel.NORMAL,
            threat_level=ThreatLevel.NONE,
            ram_only=True,
            logs_suppressed=False,
            fake_identity_active=True,
            last_threat_check=datetime.now(),
            anomalies_detected=0,
        )

        assert status.level == StealthLevel.NORMAL
        assert status.ram_only is True
        assert status.anomalies_detected == 0

