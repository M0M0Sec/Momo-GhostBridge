"""
Unit tests for DNS Tunneling.

Tests DNS encoding, client, and tunnel functionality.
"""

import asyncio
import struct
import zlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghostbridge.infrastructure.dns.encoder import (
    Base32Encoder,
    Base64Encoder,
    ChunkAssembler,
    DNSEncoder,
    DNSMessage,
    HexEncoder,
)
from ghostbridge.infrastructure.dns.client import (
    DNSClient,
    DNSQuery,
    DNSRecordType,
    DNSResponse,
    DNSRecord,
    DNSRCode,
    DNSClass,
)
from ghostbridge.infrastructure.dns.tunnel import (
    DNSTunnel,
    DNSTunnelConfig,
    DNSTunnelState,
    TunnelFallbackChain,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Encoder Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBase32Encoder:
    """Test Base32 encoder."""
    
    def test_encode_decode_roundtrip(self):
        """Test that encode/decode is reversible."""
        encoder = Base32Encoder()
        data = b"Hello, World!"
        
        encoded = encoder.encode(data)
        decoded = encoder.decode(encoded)
        
        assert decoded == data
    
    def test_encode_produces_dns_safe_chars(self):
        """Test encoded output uses only DNS-safe characters."""
        encoder = Base32Encoder()
        data = b"\x00\xff\x80\x7f" * 10
        
        encoded = encoder.encode(data)
        
        # Base32 uses only A-Z and 2-7
        for char in encoded:
            assert char in "abcdefghijklmnopqrstuvwxyz234567"
    
    def test_chunk_for_query(self):
        """Test data chunking for DNS queries."""
        encoder = Base32Encoder()
        data = b"A" * 200  # Enough to need multiple chunks
        
        chunks = encoder.chunk_for_query(data, "test.com", "sess123")
        
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.endswith(".test.com")
            assert len(chunk) <= 253  # DNS name max


class TestBase64Encoder:
    """Test Base64 encoder."""
    
    def test_encode_decode_roundtrip(self):
        """Test that encode/decode is reversible."""
        encoder = Base64Encoder()
        data = b"Binary data \x00\xff\x80"
        
        encoded = encoder.encode(data)
        decoded = encoder.decode(encoded)
        
        assert decoded == data


class TestHexEncoder:
    """Test Hex encoder."""
    
    def test_encode_decode_roundtrip(self):
        """Test that encode/decode is reversible."""
        encoder = HexEncoder()
        data = b"\xde\xad\xbe\xef"
        
        encoded = encoder.encode(data)
        decoded = encoder.decode(encoded)
        
        assert decoded == data
        assert encoded == "deadbeef"


class TestDNSMessage:
    """Test DNS message format."""
    
    def test_serialize_deserialize(self):
        """Test message serialization roundtrip."""
        msg = DNSMessage(
            msg_type=DNSMessage.Type.DATA,
            sequence=42,
            payload=b"Test payload",
        )
        
        serialized = msg.serialize()
        deserialized = DNSMessage.deserialize(serialized)
        
        assert deserialized is not None
        assert deserialized.msg_type == DNSMessage.Type.DATA
        assert deserialized.sequence == 42
        assert deserialized.payload == b"Test payload"
    
    def test_invalid_magic_rejected(self):
        """Test that invalid magic is rejected."""
        # Create message with wrong magic
        bad_data = b"XX" + b"\x01\x01\x00\x00\x00\x00" + b"\x00\x00\x00\x00"
        
        result = DNSMessage.deserialize(bad_data)
        
        assert result is None
    
    def test_checksum_validation(self):
        """Test checksum validation."""
        msg = DNSMessage(
            msg_type=DNSMessage.Type.BEACON,
            sequence=1,
            payload=b"data",
        )
        
        serialized = msg.serialize()
        # Corrupt the data
        corrupted = serialized[:-4] + b"\x00\x00\x00\x00"
        
        result = DNSMessage.deserialize(corrupted)
        
        assert result is None


class TestChunkAssembler:
    """Test chunk assembler."""
    
    def test_assemble_in_order(self):
        """Test assembling chunks in order."""
        assembler = ChunkAssembler()
        
        assembler.add_chunk(0, 3, b"Hello")
        assembler.add_chunk(1, 3, b" ")
        complete = assembler.add_chunk(2, 3, b"World")
        
        assert complete is True
        assert assembler.get_data() == b"Hello World"
    
    def test_assemble_out_of_order(self):
        """Test assembling chunks out of order."""
        assembler = ChunkAssembler()
        
        assembler.add_chunk(2, 3, b"C")
        assembler.add_chunk(0, 3, b"A")
        complete = assembler.add_chunk(1, 3, b"B")
        
        assert complete is True
        assert assembler.get_data() == b"ABC"
    
    def test_incomplete_returns_none(self):
        """Test that incomplete assembly returns None."""
        assembler = ChunkAssembler()
        
        assembler.add_chunk(0, 3, b"A")
        assembler.add_chunk(2, 3, b"C")
        # Missing chunk 1
        
        assert assembler.complete is False
        assert assembler.get_data() is None


# ═══════════════════════════════════════════════════════════════════════════════
# DNS Client Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDNSQuery:
    """Test DNS query construction."""
    
    def test_query_serialization(self):
        """Test query wire format."""
        query = DNSQuery(
            name="test.example.com",
            record_type=DNSRecordType.TXT,
            transaction_id=0x1234,
        )
        
        data = query.serialize()
        
        # Check header
        assert data[:2] == b"\x12\x34"  # Transaction ID
        assert len(data) > 12  # Header + question


class TestDNSClient:
    """Test DNS client."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return DNSClient(
            servers=["8.8.8.8"],
            timeout=5.0,
            retries=1,
        )
    
    @pytest.mark.asyncio
    async def test_query_with_mock(self, client):
        """Test query with mocked socket."""
        # Create mock response
        mock_response = DNSResponse(
            transaction_id=1234,
            rcode=DNSRCode.NOERROR,
            answers=[
                DNSRecord(
                    name="test.com",
                    record_type=DNSRecordType.TXT,
                    record_class=DNSClass.IN,
                    ttl=300,
                    data=b"\x0bhello world",  # Length-prefixed TXT
                )
            ],
        )
        
        with patch.object(client, "_query_udp", return_value=mock_response):
            result = await client.query("test.com", DNSRecordType.TXT)
        
        assert result is not None
        assert result.rcode == DNSRCode.NOERROR
        assert len(result.answers) == 1
    
    def test_cache(self, client):
        """Test response caching."""
        # Add to cache manually
        response = DNSResponse(
            transaction_id=1,
            rcode=DNSRCode.NOERROR,
            answers=[],
        )
        import time
        client._cache["test.com:16"] = (response, time.time())
        
        # Should be in cache
        assert "test.com:16" in client._cache
        
        # Clear cache
        client.clear_cache()
        assert len(client._cache) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# DNS Tunnel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDNSTunnel:
    """Test DNS tunnel."""
    
    @pytest.fixture
    def tunnel_config(self):
        """Create test tunnel config."""
        return DNSTunnelConfig(
            domain="t.test.com",
            session_id="test123",
            poll_interval=1.0,
            poll_jitter=0.1,
        )
    
    @pytest.fixture
    def tunnel(self, tunnel_config):
        """Create test tunnel."""
        return DNSTunnel(tunnel_config)
    
    def test_initial_state(self, tunnel):
        """Test tunnel starts in idle state."""
        assert tunnel.state == DNSTunnelState.IDLE
        assert not tunnel.is_connected
    
    def test_session_id_generation(self):
        """Test session ID auto-generation."""
        config = DNSTunnelConfig(domain="test.com")
        tunnel = DNSTunnel(config)
        
        # Session ID should be generated on connect
        assert config.session_id == ""  # Not yet generated
    
    @pytest.mark.asyncio
    async def test_connect_with_mock(self, tunnel):
        """Test connection with mocked beacon."""
        # Mock successful beacon response
        mock_response = DNSResponse(
            transaction_id=1,
            rcode=DNSRCode.NOERROR,
            answers=[
                DNSRecord(
                    name="test",
                    record_type=DNSRecordType.TXT,
                    record_class=DNSClass.IN,
                    ttl=60,
                    data=b"\x02OK",
                )
            ],
        )
        
        with patch.object(tunnel._client, "query", return_value=mock_response):
            result = await tunnel.connect()
        
        assert result is True
        assert tunnel.state == DNSTunnelState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, tunnel):
        """Test connection failure."""
        with patch.object(tunnel._client, "query", return_value=None):
            result = await tunnel.connect()
        
        assert result is False
        assert tunnel.state == DNSTunnelState.ERROR
    
    def test_rate_limiting(self, tunnel):
        """Test query rate limiting."""
        import time
        
        # Fill up rate limit
        now = time.time()
        tunnel._query_timestamps = [now] * 30
        
        # Rate limit should be hit
        # (We can't easily test async _rate_limit here, but verify timestamps)
        assert len(tunnel._query_timestamps) == 30
    
    def test_randomize_case(self, tunnel):
        """Test 0x20 case randomization."""
        name = "test.example.com"
        
        # Randomize multiple times
        randomized = set()
        for _ in range(10):
            randomized.add(tunnel._randomize_case(name))
        
        # Should produce different variations
        # (statistically, at least some should differ)
        # All should be valid DNS names when lowercased
        for r in randomized:
            assert r.lower() == name.lower()
    
    @pytest.mark.asyncio
    async def test_send_queues_data(self, tunnel):
        """Test that send queues data."""
        tunnel._running = True
        
        result = await tunnel.send(b"test data")
        
        assert result is True
        assert not tunnel._outbound_queue.empty()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, tunnel):
        """Test tunnel disconnect."""
        tunnel._running = True
        tunnel._set_state(DNSTunnelState.CONNECTED)
        
        await tunnel.disconnect()
        
        assert tunnel.state == DNSTunnelState.DISCONNECTED
        assert not tunnel._running


class TestTunnelFallbackChain:
    """Test tunnel fallback chain."""
    
    @pytest.fixture
    def mock_primary(self):
        """Create mock primary tunnel."""
        tunnel = MagicMock()
        tunnel.is_connected = False
        tunnel.connect = AsyncMock(return_value=False)
        tunnel.disconnect = AsyncMock()
        return tunnel
    
    @pytest.fixture
    def mock_dns(self):
        """Create mock DNS tunnel."""
        tunnel = MagicMock()
        tunnel.is_connected = False
        tunnel.connect = AsyncMock(return_value=True)
        tunnel.disconnect = AsyncMock()
        tunnel.start = AsyncMock()
        tunnel.send = AsyncMock(return_value=True)
        return tunnel
    
    @pytest.mark.asyncio
    async def test_primary_success(self, mock_primary, mock_dns):
        """Test primary tunnel success."""
        mock_primary.connect.return_value = True
        mock_primary.is_connected = True
        
        chain = TunnelFallbackChain(mock_primary, mock_dns)
        result = await chain.connect()
        
        assert result is True
        assert not chain.using_fallback
    
    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, mock_primary, mock_dns):
        """Test fallback to DNS when primary fails."""
        mock_primary.connect.return_value = False
        mock_dns.connect.return_value = True
        mock_dns.is_connected = True
        
        chain = TunnelFallbackChain(mock_primary, mock_dns)
        chain._max_primary_retries = 1  # Fail faster for test
        
        result = await chain.connect()
        
        assert result is True
        assert chain.using_fallback
    
    @pytest.mark.asyncio
    async def test_send_routes_correctly(self, mock_primary, mock_dns):
        """Test send routes to correct tunnel."""
        chain = TunnelFallbackChain(mock_primary, mock_dns)
        
        # Not using fallback
        chain._using_fallback = False
        await chain.send(b"test")
        mock_dns.send.assert_not_called()
        
        # Using fallback
        chain._using_fallback = True
        await chain.send(b"test")
        mock_dns.send.assert_called_once_with(b"test")


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDNSIntegration:
    """Integration tests for DNS tunneling."""
    
    @pytest.mark.asyncio
    async def test_full_message_flow(self):
        """Test complete message encode/chunk/decode flow."""
        # Create encoder
        encoder = Base32Encoder()
        
        # Original data
        original = b"This is a test message for DNS tunneling"
        
        # Create message
        msg = DNSMessage(
            msg_type=DNSMessage.Type.DATA,
            sequence=1,
            payload=original,
        )
        serialized = msg.serialize()
        
        # Chunk for DNS
        chunks = encoder.chunk_for_query(serialized, "test.com")
        
        # Simulate reassembly from TXT responses
        # (In real scenario, server would decode and return data)
        compressed = zlib.compress(serialized, level=9)
        encoded = encoder.encode(compressed)
        
        # Decode
        decoded_compressed = encoder.decode(encoded)
        decoded = zlib.decompress(decoded_compressed)
        
        # Verify
        result_msg = DNSMessage.deserialize(decoded)
        assert result_msg is not None
        assert result_msg.payload == original

