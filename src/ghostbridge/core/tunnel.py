"""
Tunnel Manager - Core tunnel orchestration

Manages tunnel lifecycle with automatic reconnection and health monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ghostbridge.core.config import GhostBridgeConfig, TunnelConfig
from ghostbridge.infrastructure.wireguard.config import WireGuardConfig
from ghostbridge.infrastructure.wireguard.manager import (
    TunnelStatus,
    WireGuardManager,
)

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """High-level connection state."""

    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


@dataclass
class ConnectionStats:
    """Connection statistics."""

    connect_time: datetime | None = None
    disconnect_time: datetime | None = None
    total_connects: int = 0
    total_disconnects: int = 0
    total_bytes_rx: int = 0
    total_bytes_tx: int = 0
    last_handshake: datetime | None = None
    reconnect_attempts: int = 0

    @property
    def uptime_seconds(self) -> float:
        """Get current connection uptime."""
        if not self.connect_time:
            return 0.0
        end_time = self.disconnect_time or datetime.now()
        return (end_time - self.connect_time).total_seconds()


@dataclass
class ReconnectPolicy:
    """Reconnection policy configuration."""

    delays: list[int] = field(default_factory=lambda: [5, 10, 30, 60, 300])
    max_attempts: int = 0  # 0 = unlimited
    jitter_percent: float = 0.2  # ±20% jitter
    reset_after_success: int = 300  # Reset delay index after 5 min connected

    def get_delay(self, attempt: int) -> float:
        """
        Get delay for given attempt number.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds with jitter
        """
        # Get base delay
        if attempt >= len(self.delays):
            base_delay = self.delays[-1]
        else:
            base_delay = self.delays[attempt]

        # Add jitter
        jitter = base_delay * self.jitter_percent
        delay = base_delay + random.uniform(-jitter, jitter)

        return max(1.0, delay)

    def should_retry(self, attempt: int) -> bool:
        """Check if should retry based on attempt count."""
        if self.max_attempts == 0:
            return True
        return attempt < self.max_attempts


class TunnelManager:
    """
    High-level tunnel manager with automatic reconnection.

    Features:
    - Automatic reconnection with exponential backoff
    - Health monitoring
    - Connection statistics
    - State change callbacks
    """

    def __init__(
        self,
        config: GhostBridgeConfig,
        reconnect_policy: ReconnectPolicy | None = None,
    ):
        """
        Initialize TunnelManager.

        Args:
            config: GhostBridge configuration
            reconnect_policy: Reconnection policy (uses config delays if None)
        """
        self.config = config
        self.reconnect_policy = reconnect_policy or ReconnectPolicy(
            delays=config.tunnel.reconnect_delays
        )

        # Build WireGuard config from main config
        wg_config = self._build_wg_config(config.tunnel)
        self._wireguard = WireGuardManager(wg_config)

        self._state = ConnectionState.IDLE
        self._stats = ConnectionStats()
        self._monitor_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._on_state_change: Callable[[ConnectionState], None] | None = None

    def _build_wg_config(self, tunnel_config: TunnelConfig) -> WireGuardConfig:
        """Build WireGuard config from tunnel config."""
        wg = WireGuardConfig(
            interface=tunnel_config.interface,
            address="10.66.66.2/24",
        )

        # Add C2 peer if endpoint is configured
        # Note: Actual public key should be set via WireGuard config file
        # or environment variable GHOSTBRIDGE_WG_PEER_PUBKEY
        if tunnel_config.endpoint:
            import os
            peer_pubkey = os.environ.get("GHOSTBRIDGE_WG_PEER_PUBKEY", "")
            if peer_pubkey:
                wg.add_peer(
                    public_key=peer_pubkey,
                    endpoint=tunnel_config.endpoint,
                    allowed_ips=["10.66.66.0/24"],
                    keepalive=tunnel_config.keepalive,
                )

        return wg

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def stats(self) -> ConnectionStats:
        """Get connection statistics."""
        return self._stats

    @property
    def is_connected(self) -> bool:
        """Check if tunnel is connected."""
        return self._state == ConnectionState.CONNECTED

    def on_state_change(self, callback: Callable[[ConnectionState], None]) -> None:
        """Register state change callback."""
        self._on_state_change = callback

    def _set_state(self, state: ConnectionState) -> None:
        """Update state and notify callback."""
        if state != self._state:
            old_state = self._state
            self._state = state
            logger.info(f"Connection state: {old_state.value} -> {state.value}")
            if self._on_state_change:
                try:
                    self._on_state_change(state)
                except Exception as e:
                    logger.warning(f"State callback error: {e}")

    async def connect(self) -> bool:
        """
        Establish tunnel connection.

        Returns:
            True if connected successfully
        """
        if self._state == ConnectionState.CONNECTED:
            return True

        self._set_state(ConnectionState.CONNECTING)
        self._stats.reconnect_attempts = 0

        try:
            success = await self._wireguard.up()

            if success:
                # Wait for handshake
                handshake = await self._wait_for_handshake(timeout=60)

                if handshake:
                    self._set_state(ConnectionState.CONNECTED)
                    self._stats.connect_time = datetime.now()
                    self._stats.total_connects += 1
                    self._stats.disconnect_time = None
                    logger.info("Tunnel connected with handshake")
                    return True
                else:
                    logger.warning("Tunnel up but no handshake")
                    self._set_state(ConnectionState.RECONNECTING)
                    return False
            else:
                self._set_state(ConnectionState.FAILED)
                return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._set_state(ConnectionState.FAILED)
            return False

    async def disconnect(self) -> bool:
        """
        Disconnect tunnel.

        Returns:
            True if disconnected successfully
        """
        # Stop reconnection attempts
        await self._cancel_reconnect()

        success = await self._wireguard.down()

        if success:
            self._set_state(ConnectionState.DISCONNECTED)
            self._stats.disconnect_time = datetime.now()
            self._stats.total_disconnects += 1

        return success

    async def reconnect(self) -> bool:
        """
        Force reconnection.

        Returns:
            True if reconnected successfully
        """
        self._set_state(ConnectionState.RECONNECTING)

        await self._wireguard.down()
        await asyncio.sleep(1)

        return await self.connect()

    async def _wait_for_handshake(self, timeout: float = 60) -> bool:
        """Wait for WireGuard handshake."""
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            status = await self._wireguard.get_status()

            if status.is_connected:
                for peer in status.peers:
                    if peer.has_handshake:
                        self._stats.last_handshake = peer.latest_handshake
                        return True

            await asyncio.sleep(2)

        return False

    async def start_auto_reconnect(self) -> None:
        """Start automatic reconnection handler."""
        if self._reconnect_task is not None:
            return

        async def reconnect_loop() -> None:
            attempt = 0

            while not self._shutdown_event.is_set():
                try:
                    # Check if reconnection needed
                    if self._state in (ConnectionState.CONNECTED, ConnectionState.IDLE):
                        attempt = 0
                        await asyncio.sleep(5)
                        continue

                    # Check if should retry
                    if not self.reconnect_policy.should_retry(attempt):
                        logger.error(f"Max reconnect attempts ({attempt}) reached")
                        self._set_state(ConnectionState.FAILED)
                        break

                    # Calculate delay with jitter
                    delay = self.reconnect_policy.get_delay(attempt)
                    logger.info(f"Reconnecting in {delay:.1f}s (attempt {attempt + 1})")

                    await asyncio.sleep(delay)

                    if self._shutdown_event.is_set():
                        break

                    # Attempt reconnection
                    self._stats.reconnect_attempts = attempt + 1
                    success = await self.reconnect()

                    if success:
                        logger.info("Reconnection successful")
                        attempt = 0
                    else:
                        attempt += 1

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Reconnect loop error: {e}")
                    attempt += 1
                    await asyncio.sleep(5)

        self._reconnect_task = asyncio.create_task(reconnect_loop())
        logger.info("Auto-reconnect started")

    async def _cancel_reconnect(self) -> None:
        """Cancel reconnection task."""
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

    async def start_monitoring(self, interval: float = 30) -> None:
        """
        Start connection health monitoring.

        Args:
            interval: Check interval in seconds
        """
        if self._monitor_task is not None:
            return

        async def monitor_loop() -> None:
            stable_since: datetime | None = None

            while not self._shutdown_event.is_set():
                try:
                    await asyncio.sleep(interval)

                    if self._state != ConnectionState.CONNECTED:
                        stable_since = None
                        continue

                    # Check handshake age
                    handshake_age = await self._wireguard.get_handshake_age()

                    if handshake_age is None or handshake_age > 180:
                        # No handshake or stale (3+ minutes)
                        logger.warning(f"Stale handshake: {handshake_age}s")
                        self._set_state(ConnectionState.RECONNECTING)
                        stable_since = None
                    else:
                        # Connection healthy
                        if stable_since is None:
                            stable_since = datetime.now()

                        # Update stats
                        status = await self._wireguard.get_status()
                        for peer in status.peers:
                            self._stats.total_bytes_rx = peer.transfer_rx
                            self._stats.total_bytes_tx = peer.transfer_tx
                            if peer.latest_handshake:
                                self._stats.last_handshake = peer.latest_handshake

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Monitor error: {e}")

        self._monitor_task = asyncio.create_task(monitor_loop())
        logger.info("Connection monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop connection monitoring."""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def get_status(self) -> TunnelStatus:
        """Get current tunnel status."""
        return await self._wireguard.get_status()

    async def run(self) -> None:
        """
        Run tunnel with auto-reconnect and monitoring.

        This is the main entry point for running the tunnel as a service.
        """
        try:
            # Initial connection
            await self.connect()

            # Start background tasks
            await self.start_auto_reconnect()
            await self.start_monitoring()

            # Wait for shutdown
            await self._shutdown_event.wait()

        finally:
            await self.stop_monitoring()
            await self._cancel_reconnect()
            await self.disconnect()

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()

