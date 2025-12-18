"""
Pytest configuration and shared fixtures for GhostBridge tests.
"""

import asyncio
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir() -> Path:
    """Get path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create temporary config directory."""
    config_dir = tmp_path / "ghostbridge"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def sample_config_dict() -> dict:
    """Sample configuration dictionary for testing."""
    return {
        "device": {
            "id": "test-device",
            "name": "Test GhostBridge",
        },
        "network": {
            "bridge_name": "br_test",
            "wan_interface": "eth0",
            "lan_interface": "eth1",
            "clone_mac": True,
        },
        "tunnel": {
            "type": "wireguard",
            "interface": "wg0",
            "endpoint": "test.example.com:51820",
            "keepalive": 25,
        },
        "beacon": {
            "enabled": True,
            "interval": 300,
            "jitter": 60,
        },
        "c2": {
            "api_endpoint": "http://10.66.66.1:8082/api/ghostbridge",
            "timeout": 30,
        },
        "stealth": {
            "ramfs_logs": True,
            "fake_identity": "Test Device",
            "panic_on_tamper": False,
        },
        "logging": {
            "level": "DEBUG",
            "to_disk": False,
        },
    }

