"""
RAM Disk Manager

Manages tmpfs mounts for RAM-only operation.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MountInfo:
    """Mount point information."""

    path: str
    fstype: str
    size: str
    used: int
    available: int
    use_percent: int


class RAMDiskManager:
    """
    Manages tmpfs (RAM disk) mounts for ephemeral storage.

    Features:
    - Create/destroy tmpfs mounts
    - Monitor usage
    - Auto-cleanup on limit
    """

    def __init__(self, sudo: bool = True):
        """
        Initialize RAMDiskManager.

        Args:
            sudo: Use sudo for mount operations
        """
        self.sudo = sudo
        self._sudo_prefix = ["sudo"] if sudo else []
        self._mounts: dict[str, MountInfo] = {}

    async def _run(self, *args: str) -> tuple[str, str, int]:
        """Run command asynchronously."""
        cmd = [*self._sudo_prefix, *args]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()
        return (
            stdout.decode().strip(),
            stderr.decode().strip(),
            proc.returncode or 0,
        )

    async def mount_tmpfs(
        self,
        path: str,
        size: str = "50M",
        mode: str = "1777",
    ) -> bool:
        """
        Mount a tmpfs filesystem.

        Args:
            path: Mount point path
            size: Size limit (e.g., "50M", "100M")
            mode: Permission mode

        Returns:
            True if successful
        """
        mount_path = Path(path)

        # Create mount point if needed
        mount_path.mkdir(parents=True, exist_ok=True)

        # Check if already mounted
        if await self.is_tmpfs(path):
            logger.info(f"tmpfs already mounted at {path}")
            return True

        # Mount tmpfs
        try:
            _, stderr, code = await self._run(
                "mount",
                "-t", "tmpfs",
                "-o", f"size={size},mode={mode}",
                "tmpfs",
                path,
            )

            if code != 0:
                logger.error(f"Failed to mount tmpfs: {stderr}")
                return False

            logger.info(f"Mounted tmpfs at {path} (size={size})")
            return True

        except Exception as e:
            logger.error(f"Mount error: {e}")
            return False

    async def unmount(self, path: str, force: bool = False) -> bool:
        """
        Unmount a filesystem.

        Args:
            path: Mount point path
            force: Force unmount

        Returns:
            True if successful
        """
        args = ["umount"]
        if force:
            args.append("-f")
        args.append(path)

        try:
            _, stderr, code = await self._run(*args)

            if code != 0:
                logger.error(f"Failed to unmount: {stderr}")
                return False

            logger.info(f"Unmounted {path}")
            return True

        except Exception as e:
            logger.error(f"Unmount error: {e}")
            return False

    async def is_tmpfs(self, path: str) -> bool:
        """
        Check if path is a tmpfs mount.

        Args:
            path: Path to check

        Returns:
            True if tmpfs
        """
        try:
            stdout, _, code = await self._run(
                "findmnt", "-n", "-o", "FSTYPE", path
            )

            return code == 0 and "tmpfs" in stdout

        except Exception:
            return False

    async def get_mount_info(self, path: str) -> Optional[MountInfo]:
        """
        Get mount point information.

        Args:
            path: Mount point path

        Returns:
            MountInfo or None
        """
        try:
            stdout, _, code = await self._run(
                "df", "-B1", path
            )

            if code != 0:
                return None

            lines = stdout.split("\n")
            if len(lines) < 2:
                return None

            parts = lines[1].split()
            if len(parts) < 6:
                return None

            # Get filesystem type
            fstype_out, _, _ = await self._run(
                "findmnt", "-n", "-o", "FSTYPE", path
            )

            return MountInfo(
                path=path,
                fstype=fstype_out.strip() or "unknown",
                size=parts[1],
                used=int(parts[2]),
                available=int(parts[3]),
                use_percent=int(parts[4].rstrip("%")),
            )

        except Exception as e:
            logger.error(f"Failed to get mount info: {e}")
            return None

    async def get_usage_percent(self, path: str) -> Optional[int]:
        """
        Get usage percentage of mount.

        Args:
            path: Mount point path

        Returns:
            Usage percentage or None
        """
        info = await self.get_mount_info(path)
        return info.use_percent if info else None

    async def cleanup_if_full(
        self,
        path: str,
        threshold: int = 90,
        pattern: str = "*",
    ) -> int:
        """
        Clean up old files if mount exceeds threshold.

        Args:
            path: Mount point path
            threshold: Usage threshold percentage
            pattern: File pattern to clean

        Returns:
            Number of files removed
        """
        usage = await self.get_usage_percent(path)

        if usage is None or usage < threshold:
            return 0

        logger.warning(f"Mount {path} at {usage}% - cleaning up")

        mount_path = Path(path)
        files = sorted(
            mount_path.glob(pattern),
            key=lambda f: f.stat().st_mtime if f.is_file() else 0,
        )

        removed = 0
        for file in files:
            if file.is_file():
                try:
                    file.unlink()
                    removed += 1

                    # Check if we're below threshold now
                    new_usage = await self.get_usage_percent(path)
                    if new_usage and new_usage < threshold - 10:
                        break

                except (PermissionError, OSError):
                    pass

        logger.info(f"Cleaned up {removed} files from {path}")
        return removed

    async def setup_standard_mounts(self) -> dict[str, bool]:
        """
        Setup standard tmpfs mounts for GhostBridge.

        Returns:
            Dict of path -> success
        """
        mounts = {
            "/var/log": "50M",
            "/tmp": "100M",
            "/var/ghostbridge/run": "10M",
            "/var/ghostbridge/log": "20M",
        }

        results = {}

        for path, size in mounts.items():
            results[path] = await self.mount_tmpfs(path, size)

        return results

