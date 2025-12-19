"""
IPRoute - Low-level iproute2 wrapper

Provides async interface to Linux networking commands:
- ip link (interface management)
- ip addr (address management)
- bridge (bridge management)
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class InterfaceState(Enum):
    """Network interface operational state."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class InterfaceInfo:
    """Network interface information."""

    name: str
    mac_address: str
    state: InterfaceState
    mtu: int
    master: str | None = None  # Bridge master if enslaved
    flags: list[str] | None = None

    @property
    def is_up(self) -> bool:
        """Check if interface is up."""
        return self.state == InterfaceState.UP

    @property
    def is_bridge_member(self) -> bool:
        """Check if interface is a bridge member."""
        return self.master is not None


class IPRouteError(Exception):
    """Exception raised for iproute2 command errors."""

    def __init__(self, command: str, returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{command}' failed with code {returncode}: {stderr}")


class IPRoute:
    """
    Async wrapper for iproute2 commands.

    Provides high-level interface to Linux networking operations
    without requiring external Python libraries.
    """

    # MAC address regex pattern
    MAC_PATTERN = re.compile(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}")

    def __init__(self, sudo: bool = True):
        """
        Initialize IPRoute wrapper.

        Args:
            sudo: Use sudo for privileged operations
        """
        self.sudo = sudo
        self._sudo_prefix = ["sudo"] if sudo else []

    async def _run(self, *args: str, check: bool = True) -> tuple[str, str, int]:
        """
        Run a command asynchronously.

        Args:
            *args: Command and arguments
            check: Raise exception on non-zero exit

        Returns:
            Tuple of (stdout, stderr, returncode)

        Raises:
            IPRouteError: If command fails and check=True
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
            raise IPRouteError(cmd_str, proc.returncode or 1, stderr_str)

        return stdout_str, stderr_str, proc.returncode or 0

    # ========== Interface Operations ==========

    async def interface_exists(self, name: str) -> bool:
        """
        Check if a network interface exists.

        Args:
            name: Interface name

        Returns:
            True if interface exists
        """
        try:
            await self._run("ip", "link", "show", name)
            return True
        except IPRouteError:
            return False

    async def get_interface_info(self, name: str) -> InterfaceInfo:
        """
        Get detailed interface information.

        Args:
            name: Interface name

        Returns:
            InterfaceInfo object

        Raises:
            IPRouteError: If interface doesn't exist
        """
        stdout, _, _ = await self._run("ip", "-o", "link", "show", name)

        # Parse output: "2: eth0: <BROADCAST,MULTICAST,UP> mtu 1500 ... link/ether aa:bb:cc:dd:ee:ff ..."
        parts = stdout.split()

        # Extract interface name (remove colon)
        iface_name = parts[1].rstrip(":")

        # Extract flags
        flags_match = re.search(r"<([^>]+)>", stdout)
        flags = flags_match.group(1).split(",") if flags_match else []

        # Determine state
        state = InterfaceState.UP if "UP" in flags else InterfaceState.DOWN

        # Extract MTU
        mtu = 1500
        if "mtu" in parts:
            mtu_idx = parts.index("mtu")
            mtu = int(parts[mtu_idx + 1])

        # Extract MAC address
        mac_match = self.MAC_PATTERN.search(stdout)
        mac_address = mac_match.group(0) if mac_match else "00:00:00:00:00:00"

        # Check for master (bridge membership)
        master = None
        if "master" in parts:
            master_idx = parts.index("master")
            master = parts[master_idx + 1]

        return InterfaceInfo(
            name=iface_name,
            mac_address=mac_address,
            state=state,
            mtu=mtu,
            master=master,
            flags=flags,
        )

    async def set_interface_up(self, name: str) -> None:
        """
        Bring interface up.

        Args:
            name: Interface name
        """
        await self._run("ip", "link", "set", name, "up")
        logger.info(f"Interface {name} is now UP")

    async def set_interface_down(self, name: str) -> None:
        """
        Bring interface down.

        Args:
            name: Interface name
        """
        await self._run("ip", "link", "set", name, "down")
        logger.info(f"Interface {name} is now DOWN")

    async def set_mac_address(self, name: str, mac: str) -> None:
        """
        Set interface MAC address.

        Note: Interface must be down to change MAC.

        Args:
            name: Interface name
            mac: MAC address (format: aa:bb:cc:dd:ee:ff)
        """
        if not self.MAC_PATTERN.match(mac):
            raise ValueError(f"Invalid MAC address format: {mac}")

        # Interface must be down to change MAC
        await self.set_interface_down(name)
        await self._run("ip", "link", "set", name, "address", mac)
        await self.set_interface_up(name)
        logger.info(f"Set {name} MAC to {mac}")

    async def set_promiscuous(self, name: str, enable: bool = True) -> None:
        """
        Enable/disable promiscuous mode on interface.

        Args:
            name: Interface name
            enable: True to enable, False to disable
        """
        mode = "on" if enable else "off"
        await self._run("ip", "link", "set", name, "promisc", mode)
        logger.info(f"Promiscuous mode {mode} for {name}")

    async def get_mac_address(self, name: str) -> str:
        """
        Get interface MAC address.

        Args:
            name: Interface name

        Returns:
            MAC address string
        """
        info = await self.get_interface_info(name)
        return info.mac_address

    async def read_mac_from_sysfs(self, name: str) -> str:
        """
        Read MAC address directly from sysfs.

        This is faster than parsing ip command output.

        Args:
            name: Interface name

        Returns:
            MAC address string
        """
        path = Path(f"/sys/class/net/{name}/address")
        if not path.exists():
            raise IPRouteError(f"cat {path}", 1, f"Interface {name} not found")

        return path.read_text().strip()

    # ========== Bridge Operations ==========

    async def create_bridge(self, name: str) -> None:
        """
        Create a Linux bridge interface.

        Args:
            name: Bridge name
        """
        if await self.interface_exists(name):
            logger.warning(f"Bridge {name} already exists")
            return

        await self._run("ip", "link", "add", name, "type", "bridge")
        logger.info(f"Created bridge {name}")

    async def delete_bridge(self, name: str) -> None:
        """
        Delete a Linux bridge interface.

        Args:
            name: Bridge name
        """
        if not await self.interface_exists(name):
            logger.warning(f"Bridge {name} doesn't exist")
            return

        await self.set_interface_down(name)
        await self._run("ip", "link", "delete", name, "type", "bridge")
        logger.info(f"Deleted bridge {name}")

    async def add_interface_to_bridge(self, interface: str, bridge: str) -> None:
        """
        Add an interface to a bridge.

        Args:
            interface: Interface to add
            bridge: Bridge name
        """
        await self._run("ip", "link", "set", interface, "master", bridge)
        logger.info(f"Added {interface} to bridge {bridge}")

    async def remove_interface_from_bridge(self, interface: str) -> None:
        """
        Remove an interface from its bridge.

        Args:
            interface: Interface to remove
        """
        await self._run("ip", "link", "set", interface, "nomaster")
        logger.info(f"Removed {interface} from bridge")

    async def set_bridge_stp(self, name: str, enable: bool = False) -> None:
        """
        Enable/disable STP (Spanning Tree Protocol) on bridge.

        Note: STP should be disabled for stealth operation.

        Args:
            name: Bridge name
            enable: True to enable, False to disable
        """
        value = "1" if enable else "0"
        stp_path = Path(f"/sys/class/net/{name}/bridge/stp_state")

        if not stp_path.exists():
            raise IPRouteError(f"echo > {stp_path}", 1, f"Bridge {name} not found")

        # Use tee to write as root
        await self._run("tee", str(stp_path), check=False)
        proc = await asyncio.create_subprocess_exec(
            *self._sudo_prefix,
            "tee",
            str(stp_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate(value.encode())

        logger.info(f"STP {'enabled' if enable else 'disabled'} on {name}")

    async def get_bridge_members(self, name: str) -> list[str]:
        """
        Get list of interfaces attached to a bridge.

        Args:
            name: Bridge name

        Returns:
            List of interface names
        """
        stdout, _, _ = await self._run("ip", "-o", "link", "show", "master", name, check=False)

        if not stdout:
            return []

        members = []
        for line in stdout.split("\n"):
            parts = line.split(":")
            if len(parts) >= 2:
                iface = parts[1].strip().split("@")[0]
                members.append(iface)

        return members

    # ========== Address Operations ==========

    async def flush_addresses(self, name: str) -> None:
        """
        Remove all IP addresses from interface.

        Args:
            name: Interface name
        """
        await self._run("ip", "addr", "flush", "dev", name)
        logger.info(f"Flushed all addresses from {name}")

    async def add_address(self, name: str, address: str) -> None:
        """
        Add IP address to interface.

        Args:
            name: Interface name
            address: IP address with prefix (e.g., "10.0.0.1/24")
        """
        await self._run("ip", "addr", "add", address, "dev", name)
        logger.info(f"Added {address} to {name}")

    # ========== ARP Operations ==========

    async def disable_arp(self, name: str) -> None:
        """
        Disable ARP on interface.

        Args:
            name: Interface name
        """
        await self._run("ip", "link", "set", name, "arp", "off")
        logger.info(f"ARP disabled on {name}")

    async def enable_arp(self, name: str) -> None:
        """
        Enable ARP on interface.

        Args:
            name: Interface name
        """
        await self._run("ip", "link", "set", name, "arp", "on")
        logger.info(f"ARP enabled on {name}")

    async def get_arp_table(self) -> list[dict[str, str]]:
        """
        Get system ARP table.

        Returns:
            List of dicts with ip, mac, interface keys
        """
        stdout, _, _ = await self._run("ip", "neigh", "show")

        entries = []
        for line in stdout.split("\n"):
            if not line:
                continue

            parts = line.split()
            if len(parts) >= 5 and "lladdr" in parts:
                ip = parts[0]
                dev_idx = parts.index("dev")
                lladdr_idx = parts.index("lladdr")
                entries.append(
                    {
                        "ip": ip,
                        "mac": parts[lladdr_idx + 1],
                        "interface": parts[dev_idx + 1],
                        "state": parts[-1] if parts[-1] in ("REACHABLE", "STALE", "DELAY", "PROBE") else "UNKNOWN",
                    }
                )

        return entries

    # ========== Link Detection ==========

    async def has_carrier(self, name: str) -> bool:
        """
        Check if interface has carrier (cable connected).

        Args:
            name: Interface name

        Returns:
            True if carrier detected
        """
        carrier_path = Path(f"/sys/class/net/{name}/carrier")
        if not carrier_path.exists():
            return False

        try:
            return carrier_path.read_text().strip() == "1"
        except OSError:
            return False

    async def wait_for_carrier(
        self, name: str, timeout: float = 30.0, poll_interval: float = 0.5
    ) -> bool:
        """
        Wait for interface to detect carrier.

        Args:
            name: Interface name
            timeout: Maximum wait time in seconds
            poll_interval: Time between checks

        Returns:
            True if carrier detected, False if timeout
        """
        import time

        start = time.monotonic()

        while time.monotonic() - start < timeout:
            if await self.has_carrier(name):
                return True
            await asyncio.sleep(poll_interval)

        return False

