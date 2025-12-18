"""
WireGuard Manager

High-level WireGuard tunnel management with status monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from ghostbridge.infrastructure.wireguard.config import WireGuardConfig

logger = logging.getLogger(__name__)


class TunnelState(Enum):
    """WireGuard tunnel state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class TunnelStatus:
    """WireGuard tunnel status information."""

    interface: str
    state: TunnelState
    public_key: str
    listen_port: Optional[int]
    peers: list[PeerStatus]
    last_error: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        """Check if tunnel is connected with active handshake."""
        if self.state != TunnelState.CONNECTED:
            return False
        return any(p.has_handshake for p in self.peers)


@dataclass
class PeerStatus:
    """WireGuard peer status."""

    public_key: str
    endpoint: Optional[str]
    allowed_ips: list[str]
    latest_handshake: Optional[datetime]
    transfer_rx: int  # bytes
    transfer_tx: int  # bytes

    @property
    def has_handshake(self) -> bool:
        """Check if peer has completed handshake."""
        return self.latest_handshake is not None

    @property
    def handshake_age_seconds(self) -> Optional[float]:
        """Get seconds since last handshake."""
        if not self.latest_handshake:
            return None
        return (datetime.now() - self.latest_handshake).total_seconds()


class WireGuardError(Exception):
    """WireGuard operation error."""

    pass


class WireGuardManager:
    """
    High-level WireGuard tunnel manager.

    Provides async interface for:
    - Tunnel lifecycle (up/down)
    - Status monitoring
    - Connection health checks
    """

    def __init__(
        self,
        config: WireGuardConfig,
        sudo: bool = True,
    ):
        """
        Initialize WireGuard manager.

        Args:
            config: WireGuard configuration
            sudo: Use sudo for privileged operations
        """
        self.config = config
        self.sudo = sudo
        self._sudo_prefix = ["sudo"] if sudo else []
        self._state = TunnelState.DISCONNECTED
        self._last_error: Optional[str] = None

    @property
    def interface(self) -> str:
        """Get interface name."""
        return self.config.interface

    @property
    def state(self) -> TunnelState:
        """Get current tunnel state."""
        return self._state

    def _set_state(self, state: TunnelState, error: Optional[str] = None) -> None:
        """Update tunnel state."""
        old_state = self._state
        self._state = state
        self._last_error = error
        if old_state != state:
            logger.info(f"Tunnel state: {old_state.value} -> {state.value}")
            if error:
                logger.error(f"Tunnel error: {error}")

    async def _run(self, *args: str, check: bool = True) -> tuple[str, str, int]:
        """
        Run a command asynchronously.

        Args:
            *args: Command and arguments
            check: Raise exception on non-zero exit

        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        cmd = [*self._sudo_prefix, *args]
        cmd_str = " ".join(cmd)

        logger.debug(f"Running: {cmd_str}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode("utf-8").strip()
        stderr_str = stderr.decode("utf-8").strip()

        if check and proc.returncode != 0:
            raise WireGuardError(f"Command failed: {cmd_str}\n{stderr_str}")

        return stdout_str, stderr_str, proc.returncode or 0

    async def is_installed(self) -> bool:
        """Check if WireGuard is installed."""
        try:
            await self._run("wg", "--version", check=False)
            return True
        except FileNotFoundError:
            return False

    async def interface_exists(self) -> bool:
        """Check if WireGuard interface exists."""
        try:
            await self._run("ip", "link", "show", self.interface)
            return True
        except WireGuardError:
            return False

    async def up(self) -> bool:
        """
        Bring WireGuard tunnel up.

        Returns:
            True if successful
        """
        self._set_state(TunnelState.CONNECTING)

        try:
            # Ensure config is saved
            config_path = self.config.save()
            logger.info(f"Saved config to {config_path}")

            # Bring interface up using wg-quick
            await self._run("wg-quick", "up", self.interface)

            self._set_state(TunnelState.CONNECTED)
            logger.info(f"Tunnel {self.interface} is UP")
            return True

        except WireGuardError as e:
            self._set_state(TunnelState.ERROR, str(e))
            return False

    async def down(self) -> bool:
        """
        Bring WireGuard tunnel down.

        Returns:
            True if successful
        """
        try:
            if await self.interface_exists():
                await self._run("wg-quick", "down", self.interface)

            self._set_state(TunnelState.DISCONNECTED)
            logger.info(f"Tunnel {self.interface} is DOWN")
            return True

        except WireGuardError as e:
            self._set_state(TunnelState.ERROR, str(e))
            return False

    async def restart(self) -> bool:
        """
        Restart WireGuard tunnel.

        Returns:
            True if successful
        """
        self._set_state(TunnelState.RECONNECTING)

        await self.down()
        await asyncio.sleep(1)
        return await self.up()

    async def get_status(self) -> TunnelStatus:
        """
        Get detailed tunnel status.

        Returns:
            TunnelStatus object
        """
        if not await self.interface_exists():
            return TunnelStatus(
                interface=self.interface,
                state=TunnelState.DISCONNECTED,
                public_key="",
                listen_port=None,
                peers=[],
            )

        try:
            stdout, _, _ = await self._run("wg", "show", self.interface)
            return self._parse_wg_show(stdout)
        except WireGuardError as e:
            return TunnelStatus(
                interface=self.interface,
                state=TunnelState.ERROR,
                public_key="",
                listen_port=None,
                peers=[],
                last_error=str(e),
            )

    def _parse_wg_show(self, output: str) -> TunnelStatus:
        """Parse wg show output into TunnelStatus."""
        lines = output.split("\n")
        public_key = ""
        listen_port = None
        peers: list[PeerStatus] = []
        current_peer: dict = {}

        for line in lines:
            line = line.strip()

            if line.startswith("public key:"):
                public_key = line.split(":", 1)[1].strip()

            elif line.startswith("listening port:"):
                listen_port = int(line.split(":", 1)[1].strip())

            elif line.startswith("peer:"):
                if current_peer:
                    peers.append(self._make_peer_status(current_peer))
                current_peer = {"public_key": line.split(":", 1)[1].strip()}

            elif line.startswith("endpoint:"):
                current_peer["endpoint"] = line.split(":", 1)[1].strip()

            elif line.startswith("allowed ips:"):
                ips = line.split(":", 1)[1].strip()
                current_peer["allowed_ips"] = [ip.strip() for ip in ips.split(",")]

            elif line.startswith("latest handshake:"):
                hs_str = line.split(":", 1)[1].strip()
                current_peer["latest_handshake"] = self._parse_handshake(hs_str)

            elif line.startswith("transfer:"):
                transfer = line.split(":", 1)[1].strip()
                rx, tx = self._parse_transfer(transfer)
                current_peer["transfer_rx"] = rx
                current_peer["transfer_tx"] = tx

        if current_peer:
            peers.append(self._make_peer_status(current_peer))

        # Determine state based on handshake
        state = TunnelState.CONNECTED
        if not peers or not any(p.has_handshake for p in peers):
            state = TunnelState.CONNECTING

        return TunnelStatus(
            interface=self.interface,
            state=state,
            public_key=public_key,
            listen_port=listen_port,
            peers=peers,
        )

    def _make_peer_status(self, data: dict) -> PeerStatus:
        """Create PeerStatus from parsed data."""
        return PeerStatus(
            public_key=data.get("public_key", ""),
            endpoint=data.get("endpoint"),
            allowed_ips=data.get("allowed_ips", []),
            latest_handshake=data.get("latest_handshake"),
            transfer_rx=data.get("transfer_rx", 0),
            transfer_tx=data.get("transfer_tx", 0),
        )

    def _parse_handshake(self, hs_str: str) -> Optional[datetime]:
        """Parse handshake time string."""
        if "never" in hs_str.lower():
            return None

        # Parse relative time like "1 minute, 30 seconds ago"
        total_seconds = 0

        # Extract numbers with units
        patterns = [
            (r"(\d+)\s*hour", 3600),
            (r"(\d+)\s*minute", 60),
            (r"(\d+)\s*second", 1),
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, hs_str)
            if match:
                total_seconds += int(match.group(1)) * multiplier

        if total_seconds > 0:
            from datetime import timedelta
            return datetime.now() - timedelta(seconds=total_seconds)

        return None

    def _parse_transfer(self, transfer_str: str) -> tuple[int, int]:
        """Parse transfer string like '1.2 MiB received, 3.4 KiB sent'."""
        rx = tx = 0

        # Parse received
        rx_match = re.search(r"([\d.]+)\s*(\w+)\s*received", transfer_str)
        if rx_match:
            rx = self._parse_size(float(rx_match.group(1)), rx_match.group(2))

        # Parse sent
        tx_match = re.search(r"([\d.]+)\s*(\w+)\s*sent", transfer_str)
        if tx_match:
            tx = self._parse_size(float(tx_match.group(1)), tx_match.group(2))

        return rx, tx

    def _parse_size(self, value: float, unit: str) -> int:
        """Convert size with unit to bytes."""
        multipliers = {
            "B": 1,
            "KiB": 1024,
            "MiB": 1024 ** 2,
            "GiB": 1024 ** 3,
            "TiB": 1024 ** 4,
        }
        return int(value * multipliers.get(unit, 1))

    async def check_connectivity(self, timeout: float = 5.0) -> bool:
        """
        Check if tunnel has connectivity.

        Tests by pinging the first peer's allowed IP.

        Args:
            timeout: Ping timeout in seconds

        Returns:
            True if ping successful
        """
        status = await self.get_status()

        if not status.is_connected:
            return False

        # Get first peer's gateway IP
        for peer in status.peers:
            for ip in peer.allowed_ips:
                # Extract network address
                network = ip.split("/")[0]
                if network not in ("0.0.0.0", "::", ""):
                    # Ping the gateway
                    try:
                        await self._run(
                            "ping", "-c", "1", "-W", str(int(timeout)),
                            network.rsplit(".", 1)[0] + ".1",
                            check=True,
                        )
                        return True
                    except WireGuardError:
                        pass

        # Try default gateway
        try:
            await self._run(
                "ping", "-c", "1", "-W", str(int(timeout)),
                "10.66.66.1",
                check=True,
            )
            return True
        except WireGuardError:
            return False

    async def get_handshake_age(self) -> Optional[float]:
        """
        Get age of last handshake in seconds.

        Returns:
            Seconds since last handshake, or None if no handshake
        """
        status = await self.get_status()

        for peer in status.peers:
            if peer.handshake_age_seconds is not None:
                return peer.handshake_age_seconds

        return None

