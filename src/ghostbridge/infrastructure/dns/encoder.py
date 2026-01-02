"""
DNS Data Encoder.

Encodes binary data for transmission via DNS queries.
Supports multiple encoding schemes for different record types.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import struct
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# DNS label max length is 63 characters
MAX_LABEL_LENGTH = 63

# DNS name max length is 253 characters
MAX_NAME_LENGTH = 253


@dataclass
class EncodedChunk:
    """A single encoded chunk for DNS transmission."""
    sequence: int
    total: int
    data: str
    checksum: str


class DNSEncoder(ABC):
    """Base class for DNS data encoders."""

    # Max data per DNS label (after encoding overhead)
    max_label_data: int = 32

    # Characters allowed in DNS labels
    allowed_chars: str = ""

    @abstractmethod
    def encode(self, data: bytes) -> str:
        """Encode binary data to DNS-safe string."""
        pass

    @abstractmethod
    def decode(self, encoded: str) -> bytes:
        """Decode DNS-safe string to binary data."""
        pass

    def chunk_for_query(
        self,
        data: bytes,
        domain: str,
        session_id: str = "",
    ) -> list[str]:
        """
        Split data into DNS query-safe chunks.

        Args:
            data: Binary data to encode
            domain: Base domain for queries
            session_id: Optional session identifier

        Returns:
            List of full DNS names to query
        """
        # Compress data first
        compressed = zlib.compress(data, level=9)

        # Encode
        encoded = self.encode(compressed)

        # Calculate available space per query
        # Format: [session].[seq]-[total].[chunk].[chunk]...[domain]
        domain_len = len(domain) + 1  # +1 for leading dot
        session_len = len(session_id) + 1 if session_id else 0
        header_len = 10  # seq-total.

        # Labels available for data
        available = MAX_NAME_LENGTH - domain_len - session_len - header_len
        labels_per_query = available // (MAX_LABEL_LENGTH + 1)  # +1 for dots
        chars_per_query = labels_per_query * (MAX_LABEL_LENGTH - 1)

        # Split into chunks
        chunks = []
        total = (len(encoded) + chars_per_query - 1) // chars_per_query

        for i in range(0, len(encoded), chars_per_query):
            chunk = encoded[i:i + chars_per_query]
            seq = len(chunks)

            # Split chunk into labels
            labels = []
            for j in range(0, len(chunk), MAX_LABEL_LENGTH - 1):
                label = chunk[j:j + MAX_LABEL_LENGTH - 1]
                labels.append(label)

            # Build full query name
            if session_id:
                name = f"{session_id}.{seq}-{total}.{'.'.join(labels)}.{domain}"
            else:
                name = f"{seq}-{total}.{'.'.join(labels)}.{domain}"

            chunks.append(name)

        return chunks

    def decode_response(self, txt_records: list[str]) -> bytes:
        """
        Decode data from DNS TXT responses.

        Args:
            txt_records: List of TXT record values

        Returns:
            Decoded binary data
        """
        # Join all records
        encoded = "".join(txt_records)

        # Decode
        compressed = self.decode(encoded)

        # Decompress
        return zlib.decompress(compressed)

    @staticmethod
    def compute_checksum(data: bytes) -> str:
        """Compute short checksum for data integrity."""
        return hashlib.md5(data).hexdigest()[:8]


class Base32Encoder(DNSEncoder):
    """
    Base32 encoder for DNS queries.

    Base32 uses only A-Z and 2-7, which are all valid in DNS labels.
    Case-insensitive, perfect for DNS which is case-insensitive.
    """

    max_label_data = 39  # 39 bytes encodes to 63 chars in base32
    allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

    def encode(self, data: bytes) -> str:
        """Encode to base32 (lowercase for DNS compatibility)."""
        return base64.b32encode(data).decode("ascii").rstrip("=").lower()

    def decode(self, encoded: str) -> bytes:
        """Decode from base32."""
        # Add padding
        padding = (8 - len(encoded) % 8) % 8
        encoded = encoded.upper() + "=" * padding
        return base64.b32decode(encoded)


class Base64Encoder(DNSEncoder):
    """
    Base64 encoder for DNS TXT records.

    More efficient than Base32 but requires TXT records
    since + and / are not valid in hostnames.
    """

    max_label_data = 48  # 48 bytes encodes to 64 chars in base64
    allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

    def encode(self, data: bytes) -> str:
        """Encode to base64."""
        return base64.b64encode(data).decode("ascii")

    def decode(self, encoded: str) -> bytes:
        """Decode from base64."""
        # Add padding if needed
        padding = (4 - len(encoded) % 4) % 4
        encoded = encoded + "=" * padding
        return base64.b64decode(encoded)


class HexEncoder(DNSEncoder):
    """
    Hexadecimal encoder for DNS.

    Less efficient but uses only 0-9 and a-f.
    Most compatible with all DNS implementations.
    """

    max_label_data = 31  # 31 bytes encodes to 62 hex chars
    allowed_chars = "0123456789abcdef"

    def encode(self, data: bytes) -> str:
        """Encode to hex."""
        return data.hex()

    def decode(self, encoded: str) -> bytes:
        """Decode from hex."""
        return bytes.fromhex(encoded)


@dataclass
class DNSMessage:
    """
    DNS tunneling message format.

    Message structure:
    - Header (8 bytes):
      - Magic (2 bytes): 0xGH
      - Version (1 byte)
      - Type (1 byte)
      - Sequence (2 bytes)
      - Length (2 bytes)
    - Payload (variable)
    - Checksum (4 bytes)
    """

    MAGIC = b'\x47\x48'  # "GH" for GhostBridge
    VERSION = 1

    class Type:
        """Message types."""
        DATA = 0x01
        ACK = 0x02
        BEACON = 0x03
        COMMAND = 0x04
        RESPONSE = 0x05
        KEEPALIVE = 0x06
        ERROR = 0xFF

    msg_type: int
    sequence: int
    payload: bytes

    def serialize(self) -> bytes:
        """Serialize message to bytes."""
        header = struct.pack(
            ">2sBBHH",
            self.MAGIC,
            self.VERSION,
            self.msg_type,
            self.sequence,
            len(self.payload),
        )

        data = header + self.payload
        checksum = zlib.crc32(data) & 0xFFFFFFFF

        return data + struct.pack(">I", checksum)

    @classmethod
    def deserialize(cls, data: bytes) -> DNSMessage | None:
        """Deserialize message from bytes."""
        if len(data) < 12:  # Min size: 8 header + 4 checksum
            return None

        # Verify checksum
        checksum = struct.unpack(">I", data[-4:])[0]
        if zlib.crc32(data[:-4]) & 0xFFFFFFFF != checksum:
            logger.warning("DNS message checksum mismatch")
            return None

        # Parse header
        magic, version, msg_type, sequence, length = struct.unpack(
            ">2sBBHH", data[:8]
        )

        if magic != cls.MAGIC:
            logger.warning("Invalid DNS message magic")
            return None

        if version != cls.VERSION:
            logger.warning(f"Unsupported DNS message version: {version}")
            return None

        # Extract payload
        payload = data[8:8 + length]

        return cls(
            msg_type=msg_type,
            sequence=sequence,
            payload=payload,
        )


@dataclass
class ChunkAssembler:
    """
    Assembles chunked DNS data.

    Handles out-of-order arrival and duplicate detection.
    """

    expected_total: int = 0
    chunks: dict[int, bytes] = field(default_factory=dict)
    complete: bool = False

    def add_chunk(self, sequence: int, total: int, data: bytes) -> bool:
        """
        Add a chunk.

        Args:
            sequence: Chunk sequence number
            total: Total expected chunks
            data: Chunk data

        Returns:
            True if all chunks received
        """
        if self.expected_total == 0:
            self.expected_total = total
        elif self.expected_total != total:
            logger.warning(f"Total mismatch: {total} vs {self.expected_total}")
            return False

        self.chunks[sequence] = data

        if len(self.chunks) == self.expected_total:
            self.complete = True
            return True

        return False

    def get_data(self) -> bytes | None:
        """Get assembled data if complete."""
        if not self.complete:
            return None

        # Assemble in order
        result = b""
        for i in range(self.expected_total):
            if i not in self.chunks:
                logger.error(f"Missing chunk {i}")
                return None
            result += self.chunks[i]

        return result

    def reset(self) -> None:
        """Reset assembler for next message."""
        self.expected_total = 0
        self.chunks.clear()
        self.complete = False

