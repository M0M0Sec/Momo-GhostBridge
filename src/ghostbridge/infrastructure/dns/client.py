"""
DNS Client for tunneling.

Provides low-level DNS query/response handling for covert communication.
"""

from __future__ import annotations

import asyncio
import logging
import random
import socket
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class DNSRecordType(IntEnum):
    """DNS record types."""
    A = 1
    NS = 2
    CNAME = 5
    NULL = 10
    TXT = 16
    AAAA = 28


class DNSClass(IntEnum):
    """DNS classes."""
    IN = 1  # Internet


class DNSRCode(IntEnum):
    """DNS response codes."""
    NOERROR = 0
    FORMERR = 1
    SERVFAIL = 2
    NXDOMAIN = 3
    NOTIMP = 4
    REFUSED = 5


@dataclass
class DNSQuery:
    """DNS query structure."""
    name: str
    record_type: DNSRecordType = DNSRecordType.TXT
    record_class: DNSClass = DNSClass.IN
    transaction_id: int = 0
    
    def __post_init__(self):
        if self.transaction_id == 0:
            self.transaction_id = random.randint(0, 65535)
    
    def serialize(self) -> bytes:
        """Serialize to DNS wire format."""
        # Header
        # ID (2) | Flags (2) | QDCOUNT (2) | ANCOUNT (2) | NSCOUNT (2) | ARCOUNT (2)
        flags = 0x0100  # Standard query, recursion desired
        header = struct.pack(
            ">HHHHHH",
            self.transaction_id,
            flags,
            1,  # QDCOUNT
            0,  # ANCOUNT
            0,  # NSCOUNT
            0,  # ARCOUNT
        )
        
        # Question section
        question = self._encode_name(self.name)
        question += struct.pack(">HH", self.record_type, self.record_class)
        
        return header + question
    
    def _encode_name(self, name: str) -> bytes:
        """Encode domain name to DNS wire format."""
        result = b""
        for label in name.split("."):
            if label:
                encoded = label.encode("ascii")
                result += bytes([len(encoded)]) + encoded
        result += b"\x00"  # Root label
        return result


@dataclass
class DNSRecord:
    """DNS resource record."""
    name: str
    record_type: DNSRecordType
    record_class: DNSClass
    ttl: int
    data: bytes
    
    @property
    def txt_data(self) -> str:
        """Get TXT record data as string."""
        if self.record_type != DNSRecordType.TXT:
            return ""
        
        # TXT records have length-prefixed strings
        result = []
        i = 0
        while i < len(self.data):
            length = self.data[i]
            i += 1
            if i + length <= len(self.data):
                result.append(self.data[i:i + length].decode("ascii", errors="replace"))
            i += length
        
        return "".join(result)
    
    @property
    def a_data(self) -> str:
        """Get A record data as IP string."""
        if self.record_type != DNSRecordType.A or len(self.data) != 4:
            return ""
        return ".".join(str(b) for b in self.data)
    
    @property
    def cname_data(self) -> str:
        """Get CNAME record data as string."""
        if self.record_type != DNSRecordType.CNAME:
            return ""
        return self._decode_name(self.data, 0)[0]
    
    def _decode_name(self, data: bytes, offset: int) -> tuple[str, int]:
        """Decode domain name from DNS wire format."""
        labels = []
        original_offset = offset
        jumped = False
        
        while offset < len(data):
            length = data[offset]
            
            if length == 0:
                offset += 1
                break
            
            # Check for compression pointer
            if length & 0xC0 == 0xC0:
                if not jumped:
                    original_offset = offset + 2
                pointer = struct.unpack(">H", data[offset:offset + 2])[0] & 0x3FFF
                offset = pointer
                jumped = True
                continue
            
            offset += 1
            labels.append(data[offset:offset + length].decode("ascii", errors="replace"))
            offset += length
        
        return ".".join(labels), original_offset if jumped else offset


@dataclass
class DNSResponse:
    """DNS response structure."""
    transaction_id: int
    rcode: DNSRCode
    answers: list[DNSRecord] = field(default_factory=list)
    
    @classmethod
    def deserialize(cls, data: bytes, query: DNSQuery) -> "DNSResponse | None":
        """Parse DNS response from wire format."""
        if len(data) < 12:
            return None
        
        # Parse header
        tid, flags, qdcount, ancount, nscount, arcount = struct.unpack(
            ">HHHHHH", data[:12]
        )
        
        # Verify transaction ID
        if tid != query.transaction_id:
            logger.warning(f"Transaction ID mismatch: {tid} vs {query.transaction_id}")
            return None
        
        rcode = DNSRCode(flags & 0x000F)
        
        # Skip question section
        offset = 12
        for _ in range(qdcount):
            # Skip name
            while offset < len(data) and data[offset] != 0:
                if data[offset] & 0xC0 == 0xC0:
                    offset += 2
                    break
                offset += data[offset] + 1
            else:
                offset += 1
            offset += 4  # QTYPE + QCLASS
        
        # Parse answers
        answers = []
        for _ in range(ancount):
            record, offset = cls._parse_record(data, offset)
            if record:
                answers.append(record)
        
        return cls(
            transaction_id=tid,
            rcode=rcode,
            answers=answers,
        )
    
    @classmethod
    def _parse_record(
        cls,
        data: bytes,
        offset: int,
    ) -> tuple[DNSRecord | None, int]:
        """Parse a single resource record."""
        if offset + 10 > len(data):
            return None, offset
        
        # Parse name
        name, offset = cls._decode_name(data, offset)
        
        # Parse fixed fields
        rtype, rclass, ttl, rdlength = struct.unpack(
            ">HHIH", data[offset:offset + 10]
        )
        offset += 10
        
        # Parse rdata
        rdata = data[offset:offset + rdlength]
        offset += rdlength
        
        record = DNSRecord(
            name=name,
            record_type=DNSRecordType(rtype) if rtype in [e.value for e in DNSRecordType] else DNSRecordType.TXT,
            record_class=DNSClass(rclass) if rclass in [e.value for e in DNSClass] else DNSClass.IN,
            ttl=ttl,
            data=rdata,
        )
        
        return record, offset
    
    @classmethod
    def _decode_name(cls, data: bytes, offset: int) -> tuple[str, int]:
        """Decode domain name from DNS wire format."""
        labels = []
        original_offset = offset
        jumped = False
        max_jumps = 10
        jumps = 0
        
        while offset < len(data) and jumps < max_jumps:
            length = data[offset]
            
            if length == 0:
                offset += 1
                break
            
            # Check for compression pointer
            if length & 0xC0 == 0xC0:
                if offset + 1 >= len(data):
                    break
                if not jumped:
                    original_offset = offset + 2
                pointer = struct.unpack(">H", data[offset:offset + 2])[0] & 0x3FFF
                offset = pointer
                jumped = True
                jumps += 1
                continue
            
            offset += 1
            if offset + length > len(data):
                break
            labels.append(data[offset:offset + length].decode("ascii", errors="replace"))
            offset += length
        
        return ".".join(labels), original_offset if jumped else offset


class DNSClient:
    """
    Async DNS client for tunneling.
    
    Supports:
    - UDP and TCP queries
    - Multiple DNS servers with failover
    - Query retries with timeout
    - Response caching
    """
    
    def __init__(
        self,
        servers: list[str] | None = None,
        timeout: float = 5.0,
        retries: int = 3,
        use_tcp: bool = False,
    ):
        """
        Initialize DNS client.
        
        Args:
            servers: List of DNS server IPs (default: system DNS)
            timeout: Query timeout in seconds
            retries: Number of retry attempts
            use_tcp: Use TCP instead of UDP
        """
        self.servers = servers or ["8.8.8.8", "1.1.1.1"]
        self.timeout = timeout
        self.retries = retries
        self.use_tcp = use_tcp
        
        self._socket: socket.socket | None = None
        self._cache: dict[str, tuple[DNSResponse, float]] = {}
        self._cache_ttl = 300  # 5 minutes default
    
    async def query(
        self,
        name: str,
        record_type: DNSRecordType = DNSRecordType.TXT,
    ) -> DNSResponse | None:
        """
        Perform DNS query.
        
        Args:
            name: Domain name to query
            record_type: Record type (default: TXT)
            
        Returns:
            DNS response or None on failure
        """
        # Check cache
        cache_key = f"{name}:{record_type.value}"
        if cache_key in self._cache:
            response, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return response
        
        query = DNSQuery(name=name, record_type=record_type)
        query_data = query.serialize()
        
        for attempt in range(self.retries):
            for server in self.servers:
                try:
                    if self.use_tcp:
                        response = await self._query_tcp(server, query_data, query)
                    else:
                        response = await self._query_udp(server, query_data, query)
                    
                    if response and response.rcode == DNSRCode.NOERROR:
                        # Cache successful response
                        self._cache[cache_key] = (response, time.time())
                        return response
                    
                except asyncio.TimeoutError:
                    logger.debug(f"DNS query timeout: {server}")
                except Exception as e:
                    logger.debug(f"DNS query error ({server}): {e}")
            
            # Add jitter between retries
            if attempt < self.retries - 1:
                await asyncio.sleep(0.5 + random.random())
        
        return None
    
    async def _query_udp(
        self,
        server: str,
        query_data: bytes,
        query: DNSQuery,
    ) -> DNSResponse | None:
        """Perform UDP DNS query."""
        loop = asyncio.get_event_loop()
        
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        
        try:
            # Send query
            await loop.sock_sendto(sock, query_data, (server, 53))
            
            # Wait for response
            response_data = await asyncio.wait_for(
                loop.sock_recv(sock, 4096),
                timeout=self.timeout,
            )
            
            return DNSResponse.deserialize(response_data, query)
            
        finally:
            sock.close()
    
    async def _query_tcp(
        self,
        server: str,
        query_data: bytes,
        query: DNSQuery,
    ) -> DNSResponse | None:
        """Perform TCP DNS query."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(server, 53),
                timeout=self.timeout,
            )
            
            try:
                # TCP DNS prepends 2-byte length
                length = struct.pack(">H", len(query_data))
                writer.write(length + query_data)
                await writer.drain()
                
                # Read response length
                length_data = await asyncio.wait_for(
                    reader.readexactly(2),
                    timeout=self.timeout,
                )
                response_length = struct.unpack(">H", length_data)[0]
                
                # Read response
                response_data = await asyncio.wait_for(
                    reader.readexactly(response_length),
                    timeout=self.timeout,
                )
                
                return DNSResponse.deserialize(response_data, query)
                
            finally:
                writer.close()
                await writer.wait_closed()
                
        except Exception as e:
            logger.debug(f"TCP DNS error: {e}")
            return None
    
    async def send_data(
        self,
        data: str,
        domain: str,
    ) -> bool:
        """
        Send data via DNS query (exfiltration).
        
        The data is encoded in the subdomain labels.
        
        Args:
            data: Encoded data string
            domain: Base domain
            
        Returns:
            True if query was acknowledged
        """
        # Data is already in query name
        response = await self.query(f"{data}.{domain}", DNSRecordType.TXT)
        
        if response and response.answers:
            # Check for ACK in response
            for answer in response.answers:
                if answer.record_type == DNSRecordType.TXT:
                    txt = answer.txt_data
                    if txt.startswith("OK") or txt.startswith("ACK"):
                        return True
        
        return False
    
    async def receive_data(
        self,
        query_name: str,
    ) -> str | None:
        """
        Receive data via DNS TXT response.
        
        Args:
            query_name: Domain to query
            
        Returns:
            TXT record data or None
        """
        response = await self.query(query_name, DNSRecordType.TXT)
        
        if response and response.answers:
            # Collect all TXT data
            txt_data = []
            for answer in response.answers:
                if answer.record_type == DNSRecordType.TXT:
                    txt_data.append(answer.txt_data)
            return "".join(txt_data) if txt_data else None
        
        return None
    
    def clear_cache(self) -> None:
        """Clear response cache."""
        self._cache.clear()

