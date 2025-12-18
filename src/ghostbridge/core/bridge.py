"""
Bridge Manager - Core bridge orchestration

High-level bridge lifecycle management integrating configuration
and network infrastructure.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import AsyncIterator

from ghostbridge.core.config import GhostBridgeConfig
from ghostbridge.infrastructure.network.manager import (
    BridgeStatus,
    NetworkManager,
    NetworkState,
)

logger = logging.getLogger(__name__)


class BridgeMode(Enum):
    """Bridge operation mode."""

    TRANSPARENT = "transparent"  # Full L2 bridge, invisible
    MONITOR = "monitor"  # Bridge + traffic monitoring
    INTERCEPT = "intercept"  # Bridge + traffic interception (future)


@dataclass
class BridgeStats:
    """Bridge traffic statistics."""

    start_time: datetime
    uptime_seconds: float
    packets_bridged: int
    bytes_bridged: int
    wan_rx_packets: int
    wan_tx_packets: int
    lan_rx_packets: int
    lan_tx_packets: int


class BridgeManager:
    """
    Core bridge lifecycle manager.

    Coordinates:
    - Bridge setup and teardown
    - Configuration management
    - State monitoring
    - Signal handling for graceful shutdown
    """

    def __init__(
        self,
        config: GhostBridgeConfig | None = None,
        mode: BridgeMode = BridgeMode.TRANSPARENT,
    ):
        """
        Initialize BridgeManager.

        Args:
            config: GhostBridge configuration (loads default if None)
            mode: Bridge operation mode
        """
        self.config = config or GhostBridgeConfig.load()
        self.mode = mode

        # Initialize network manager from config
        bridge_name, wan_iface, lan_iface = self.config.get_bridge_interfaces()
        self._network = NetworkManager(
            bridge_name=bridge_name,
            wan_interface=wan_iface,
            lan_interface=lan_iface,
            clone_mac=self.config.network.clone_mac,
        )

        self._start_time: datetime | None = None
        self._shutdown_event = asyncio.Event()
        self._setup_complete = asyncio.Event()

    @property
    def is_active(self) -> bool:
        """Check if bridge is active."""
        return self._network.state == NetworkState.ACTIVE

    @property
    def state(self) -> NetworkState:
        """Get current network state."""
        return self._network.state

    @property
    def target_mac(self) -> str | None:
        """Get detected target MAC address."""
        return self._network.target_mac

    @property
    def uptime(self) -> float:
        """Get bridge uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    async def setup(self) -> bool:
        """
        Set up the bridge.

        Returns:
            True if setup successful
        """
        logger.info(f"Setting up bridge in {self.mode.value} mode...")
        logger.info(f"Device ID: {self.config.device.id}")
        logger.info(f"Device Name: {self.config.device.name}")

        success = await self._network.setup_bridge()

        if success:
            self._start_time = datetime.now()
            self._setup_complete.set()
            logger.info("Bridge is now active")

            # Start link monitoring
            await self._network.start_monitoring(interval=5.0)

        return success

    async def teardown(self) -> bool:
        """
        Tear down the bridge.

        Returns:
            True if teardown successful
        """
        logger.info("Tearing down bridge...")

        # Stop monitoring
        await self._network.stop_monitoring()

        # Teardown bridge
        success = await self._network.teardown_bridge()

        self._start_time = None
        self._setup_complete.clear()

        return success

    async def get_status(self) -> BridgeStatus:
        """
        Get current bridge status.

        Returns:
            BridgeStatus object
        """
        return await self._network.get_status()

    async def get_stats(self) -> BridgeStats | None:
        """
        Get bridge traffic statistics.

        Returns:
            BridgeStats or None if not active
        """
        if not self.is_active or self._start_time is None:
            return None

        # Read stats from /sys/class/net/{iface}/statistics/
        try:
            stats = await self._read_interface_stats()
            return BridgeStats(
                start_time=self._start_time,
                uptime_seconds=self.uptime,
                packets_bridged=stats["wan_rx"] + stats["lan_rx"],
                bytes_bridged=stats["wan_rx_bytes"] + stats["lan_rx_bytes"],
                wan_rx_packets=stats["wan_rx"],
                wan_tx_packets=stats["wan_tx"],
                lan_rx_packets=stats["lan_rx"],
                lan_tx_packets=stats["lan_tx"],
            )
        except Exception as e:
            logger.warning(f"Failed to read stats: {e}")
            return None

    async def _read_interface_stats(self) -> dict[str, int]:
        """Read interface statistics from sysfs."""
        import aiofiles
        from pathlib import Path

        stats = {}
        wan = self.config.network.wan_interface
        lan = self.config.network.lan_interface

        for iface, prefix in [(wan, "wan"), (lan, "lan")]:
            base = Path(f"/sys/class/net/{iface}/statistics")

            for stat, suffix in [
                ("rx_packets", "rx"),
                ("tx_packets", "tx"),
                ("rx_bytes", "rx_bytes"),
                ("tx_bytes", "tx_bytes"),
            ]:
                path = base / stat
                try:
                    value = int(path.read_text().strip())
                except (OSError, ValueError):
                    value = 0
                stats[f"{prefix}_{suffix}"] = value

        return stats

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        logger.info("Shutdown requested")
        self._shutdown_event.set()

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.request_shutdown)

        logger.debug("Signal handlers installed")

    @asynccontextmanager
    async def running(self) -> AsyncIterator[BridgeManager]:
        """
        Context manager for bridge lifecycle.

        Usage:
            async with bridge_manager.running() as bridge:
                # Bridge is active
                await bridge.wait_for_shutdown()
        """
        try:
            success = await self.setup()
            if not success:
                raise RuntimeError("Bridge setup failed")
            yield self
        finally:
            await self.teardown()

    async def run_forever(self) -> None:
        """
        Run the bridge until shutdown signal.

        This is the main entry point for running GhostBridge as a service.
        """
        self.setup_signal_handlers()

        async with self.running():
            logger.info("GhostBridge is running. Press Ctrl+C to stop.")
            await self.wait_for_shutdown()

        logger.info("GhostBridge stopped")


async def main() -> None:
    """Main entry point for bridge service."""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load configuration
    try:
        config = GhostBridgeConfig.load()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Create and run bridge
    bridge = BridgeManager(config=config)
    await bridge.run_forever()


if __name__ == "__main__":
    asyncio.run(main())

