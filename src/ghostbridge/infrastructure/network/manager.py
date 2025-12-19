"""
Network Manager - High-level network operations

Coordinates bridge setup, MAC cloning, and network monitoring.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from ghostbridge.infrastructure.network.iproute import IPRoute, IPRouteError

logger = logging.getLogger(__name__)


class NetworkState(Enum):
    """Overall network state."""

    UNCONFIGURED = "unconfigured"
    CONFIGURING = "configuring"
    ACTIVE = "active"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class BridgeStatus:
    """Bridge status information."""

    name: str
    state: NetworkState
    wan_interface: str
    lan_interface: str
    wan_link: bool
    lan_link: bool
    wan_mac: str
    lan_mac: str
    original_wan_mac: str
    members: list[str]
    error: str | None = None

    @property
    def is_active(self) -> bool:
        """Check if bridge is fully active."""
        return self.state == NetworkState.ACTIVE and self.wan_link and self.lan_link


class NetworkManager:
    """
    High-level network manager for GhostBridge.

    Handles:
    - Bridge creation and configuration
    - MAC address cloning from target
    - Link state monitoring
    - Graceful error recovery
    """

    def __init__(
        self,
        bridge_name: str = "br0",
        wan_interface: str = "eth0",
        lan_interface: str = "eth1",
        clone_mac: bool = True,
        sudo: bool = True,
    ):
        """
        Initialize NetworkManager.

        Args:
            bridge_name: Name for the bridge interface
            wan_interface: WAN interface (connects to wall port)
            lan_interface: LAN interface (connects to target device)
            clone_mac: Clone MAC address from LAN to WAN
            sudo: Use sudo for privileged operations
        """
        self.bridge_name = bridge_name
        self.wan_interface = wan_interface
        self.lan_interface = lan_interface
        self.clone_mac = clone_mac

        self._iproute = IPRoute(sudo=sudo)
        self._state = NetworkState.UNCONFIGURED
        self._original_wan_mac: str | None = None
        self._target_mac: str | None = None
        self._monitor_task: asyncio.Task | None = None
        self._on_state_change: Callable[[NetworkState], None] | None = None

    @property
    def state(self) -> NetworkState:
        """Get current network state."""
        return self._state

    @property
    def target_mac(self) -> str | None:
        """Get cloned target MAC address."""
        return self._target_mac

    def on_state_change(self, callback: Callable[[NetworkState], None]) -> None:
        """
        Register callback for state changes.

        Args:
            callback: Function to call with new state
        """
        self._on_state_change = callback

    def _set_state(self, state: NetworkState) -> None:
        """Update state and notify callback."""
        if state != self._state:
            old_state = self._state
            self._state = state
            logger.info(f"Network state: {old_state.value} -> {state.value}")
            if self._on_state_change:
                self._on_state_change(state)

    async def setup_bridge(self) -> bool:
        """
        Set up the transparent bridge.

        This is the main setup routine that:
        1. Creates the bridge interface
        2. Waits for target device on LAN
        3. Clones target MAC to WAN interface
        4. Adds interfaces to bridge
        5. Brings everything up

        Returns:
            True if setup successful, False otherwise
        """
        self._set_state(NetworkState.CONFIGURING)

        try:
            # Step 1: Verify interfaces exist
            logger.info("Verifying network interfaces...")
            for iface in [self.wan_interface, self.lan_interface]:
                if not await self._iproute.interface_exists(iface):
                    raise IPRouteError(f"ip link show {iface}", 1, f"Interface {iface} not found")

            # Step 2: Save original WAN MAC
            self._original_wan_mac = await self._iproute.get_mac_address(self.wan_interface)
            logger.info(f"Original WAN MAC: {self._original_wan_mac}")

            # Step 3: Create bridge (if not exists)
            logger.info(f"Creating bridge {self.bridge_name}...")
            await self._iproute.create_bridge(self.bridge_name)

            # Step 4: Disable STP for faster convergence and stealth
            await self._iproute.set_bridge_stp(self.bridge_name, enable=False)

            # Step 5: Wait for LAN carrier (target device)
            logger.info("Waiting for target device on LAN...")
            await self._iproute.set_interface_up(self.lan_interface)

            if not await self._iproute.wait_for_carrier(self.lan_interface, timeout=60):
                logger.warning("No target device detected on LAN, continuing anyway")

            # Step 6: Clone MAC from target (if enabled)
            if self.clone_mac:
                await self._clone_target_mac()

            # Step 7: Add interfaces to bridge
            logger.info("Adding interfaces to bridge...")
            await self._iproute.add_interface_to_bridge(self.wan_interface, self.bridge_name)
            await self._iproute.add_interface_to_bridge(self.lan_interface, self.bridge_name)

            # Step 8: Enable promiscuous mode
            await self._iproute.set_promiscuous(self.wan_interface, enable=True)
            await self._iproute.set_promiscuous(self.lan_interface, enable=True)

            # Step 9: Flush any IP addresses (bridge should be L2 only)
            await self._iproute.flush_addresses(self.wan_interface)
            await self._iproute.flush_addresses(self.lan_interface)
            await self._iproute.flush_addresses(self.bridge_name)

            # Step 10: Bring everything up
            await self._iproute.set_interface_up(self.wan_interface)
            await self._iproute.set_interface_up(self.lan_interface)
            await self._iproute.set_interface_up(self.bridge_name)

            self._set_state(NetworkState.ACTIVE)
            logger.info("Bridge setup complete!")
            return True

        except Exception as e:
            logger.error(f"Bridge setup failed: {e}")
            self._set_state(NetworkState.ERROR)
            return False

    async def _clone_target_mac(self) -> None:
        """
        Clone MAC address from target device to WAN interface.

        This makes the GhostBridge invisible to the upstream switch,
        as the same MAC appears on the wall port.
        """
        # Read target MAC from LAN interface traffic
        # For now, we just read the LAN interface's connected device
        # This will be enhanced to sniff the first packet from target

        try:
            # Wait a bit for ARP to populate
            await asyncio.sleep(2)

            # Try to get target MAC from ARP table
            arp_entries = await self._iproute.get_arp_table()
            lan_entries = [e for e in arp_entries if e["interface"] == self.lan_interface]

            if lan_entries:
                self._target_mac = lan_entries[0]["mac"]
                logger.info(f"Detected target MAC from ARP: {self._target_mac}")
            else:
                # Fallback: read connected device MAC via bridge FDB
                # For initial implementation, skip if no ARP entry
                logger.warning("Could not detect target MAC, using passive mode")
                return

            # Clone MAC to WAN interface
            await self._iproute.set_mac_address(self.wan_interface, self._target_mac)
            logger.info(f"Cloned target MAC {self._target_mac} to WAN")

        except Exception as e:
            logger.warning(f"MAC cloning failed (non-fatal): {e}")

    async def teardown_bridge(self) -> bool:
        """
        Tear down the bridge and restore original configuration.

        Returns:
            True if teardown successful
        """
        try:
            logger.info("Tearing down bridge...")

            # Remove interfaces from bridge
            for iface in [self.wan_interface, self.lan_interface]:
                try:
                    await self._iproute.remove_interface_from_bridge(iface)
                except IPRouteError:
                    pass  # May already be removed

            # Delete bridge
            await self._iproute.delete_bridge(self.bridge_name)

            # Restore original WAN MAC
            if self._original_wan_mac:
                try:
                    await self._iproute.set_mac_address(
                        self.wan_interface, self._original_wan_mac
                    )
                except IPRouteError:
                    pass

            # Disable promiscuous mode
            await self._iproute.set_promiscuous(self.wan_interface, enable=False)
            await self._iproute.set_promiscuous(self.lan_interface, enable=False)

            self._set_state(NetworkState.UNCONFIGURED)
            logger.info("Bridge teardown complete")
            return True

        except Exception as e:
            logger.error(f"Bridge teardown failed: {e}")
            return False

    async def get_status(self) -> BridgeStatus:
        """
        Get current bridge status.

        Returns:
            BridgeStatus object with current state
        """
        try:
            # Check link states
            wan_link = await self._iproute.has_carrier(self.wan_interface)
            lan_link = await self._iproute.has_carrier(self.lan_interface)

            # Get MAC addresses
            wan_mac = await self._iproute.get_mac_address(self.wan_interface)
            lan_mac = await self._iproute.get_mac_address(self.lan_interface)

            # Get bridge members
            members = await self._iproute.get_bridge_members(self.bridge_name)

            return BridgeStatus(
                name=self.bridge_name,
                state=self._state,
                wan_interface=self.wan_interface,
                lan_interface=self.lan_interface,
                wan_link=wan_link,
                lan_link=lan_link,
                wan_mac=wan_mac,
                lan_mac=lan_mac,
                original_wan_mac=self._original_wan_mac or "",
                members=members,
            )

        except Exception as e:
            return BridgeStatus(
                name=self.bridge_name,
                state=NetworkState.ERROR,
                wan_interface=self.wan_interface,
                lan_interface=self.lan_interface,
                wan_link=False,
                lan_link=False,
                wan_mac="",
                lan_mac="",
                original_wan_mac="",
                members=[],
                error=str(e),
            )

    async def start_monitoring(self, interval: float = 5.0) -> None:
        """
        Start background link monitoring.

        Args:
            interval: Check interval in seconds
        """
        if self._monitor_task is not None:
            return

        async def monitor_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self._check_link_state()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Monitor error: {e}")

        self._monitor_task = asyncio.create_task(monitor_loop())
        logger.info("Link monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background link monitoring."""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            logger.info("Link monitoring stopped")

    async def _check_link_state(self) -> None:
        """Check link state and update status."""
        if self._state not in (NetworkState.ACTIVE, NetworkState.DEGRADED):
            return

        wan_link = await self._iproute.has_carrier(self.wan_interface)
        lan_link = await self._iproute.has_carrier(self.lan_interface)

        if wan_link and lan_link:
            if self._state == NetworkState.DEGRADED:
                self._set_state(NetworkState.ACTIVE)
        else:
            if self._state == NetworkState.ACTIVE:
                self._set_state(NetworkState.DEGRADED)
                logger.warning(f"Link degraded - WAN: {wan_link}, LAN: {lan_link}")

