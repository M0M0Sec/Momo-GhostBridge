"""
Secure Wipe Module

Cryptographically secure data destruction.
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class WipeMethod(Enum):
    """Secure wipe method."""

    ZEROS = "zeros"  # Single pass zeros (fast)
    ONES = "ones"  # Single pass ones
    RANDOM = "random"  # Single pass random
    DOD_3 = "dod_3"  # DoD 5220.22-M (3 pass)
    DOD_7 = "dod_7"  # DoD 5220.22-M ECE (7 pass)
    GUTMANN = "gutmann"  # Gutmann method (35 pass)


@dataclass
class WipeResult:
    """Result of a wipe operation."""

    path: str
    success: bool
    bytes_wiped: int
    passes: int
    error: Optional[str] = None


class SecureWiper:
    """
    Secure file and directory wiping.

    Supports multiple wipe methods with verification.
    """

    # DoD 5220.22-M patterns
    DOD_PATTERNS = [
        b"\x00",  # Pass 1: zeros
        b"\xff",  # Pass 2: ones
        None,  # Pass 3: random
    ]

    # DoD ECE additional patterns
    DOD_ECE_PATTERNS = [
        b"\x00",
        b"\xff",
        None,
        b"\x00",
        None,
        b"\xff",
        None,
    ]

    def __init__(
        self,
        default_method: WipeMethod = WipeMethod.DOD_3,
        verify: bool = True,
        block_size: int = 4096,
    ):
        """
        Initialize SecureWiper.

        Args:
            default_method: Default wipe method
            verify: Verify wipe completion
            block_size: Write block size
        """
        self.default_method = default_method
        self.verify = verify
        self.block_size = block_size

    def _get_patterns(self, method: WipeMethod) -> list[Optional[bytes]]:
        """Get wipe patterns for method."""
        if method == WipeMethod.ZEROS:
            return [b"\x00"]
        elif method == WipeMethod.ONES:
            return [b"\xff"]
        elif method == WipeMethod.RANDOM:
            return [None]
        elif method == WipeMethod.DOD_3:
            return self.DOD_PATTERNS
        elif method == WipeMethod.DOD_7:
            return self.DOD_ECE_PATTERNS
        elif method == WipeMethod.GUTMANN:
            # Simplified Gutmann (35 passes with various patterns)
            patterns: list[Optional[bytes]] = []
            for _ in range(4):
                patterns.append(None)  # Random
            for i in range(27):
                patterns.append(bytes([i % 256]))
            for _ in range(4):
                patterns.append(None)  # Random
            return patterns
        else:
            return [b"\x00"]

    async def wipe_file(
        self,
        path: Path,
        method: Optional[WipeMethod] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> WipeResult:
        """
        Securely wipe a file.

        Args:
            path: File path to wipe
            method: Wipe method (uses default if None)
            progress_callback: Callback(current_pass, total_passes)

        Returns:
            WipeResult with operation details
        """
        method = method or self.default_method
        patterns = self._get_patterns(method)

        if not path.exists():
            return WipeResult(
                path=str(path),
                success=True,
                bytes_wiped=0,
                passes=0,
            )

        if not path.is_file():
            return WipeResult(
                path=str(path),
                success=False,
                bytes_wiped=0,
                passes=0,
                error="Not a file",
            )

        try:
            file_size = path.stat().st_size
            total_wiped = 0

            for pass_num, pattern in enumerate(patterns):
                if progress_callback:
                    progress_callback(pass_num + 1, len(patterns))

                # Generate data for this pass
                if pattern is None:
                    # Random data
                    await self._write_random(path, file_size)
                else:
                    # Pattern data
                    await self._write_pattern(path, file_size, pattern)

                total_wiped += file_size

                # Small delay between passes
                await asyncio.sleep(0.01)

            # Truncate to zero
            path.write_bytes(b"")

            # Rename to random name before delete (obscure original name)
            random_name = path.parent / secrets.token_hex(16)
            path.rename(random_name)

            # Delete
            random_name.unlink()

            # Verify (try to read - should fail)
            if self.verify and path.exists():
                return WipeResult(
                    path=str(path),
                    success=False,
                    bytes_wiped=total_wiped,
                    passes=len(patterns),
                    error="File still exists after wipe",
                )

            return WipeResult(
                path=str(path),
                success=True,
                bytes_wiped=total_wiped,
                passes=len(patterns),
            )

        except Exception as e:
            logger.error(f"Wipe failed for {path}: {e}")
            return WipeResult(
                path=str(path),
                success=False,
                bytes_wiped=0,
                passes=0,
                error=str(e),
            )

    async def _write_pattern(
        self,
        path: Path,
        size: int,
        pattern: bytes,
    ) -> None:
        """Write repeating pattern to file."""
        # Create block of pattern
        block = (pattern * self.block_size)[:self.block_size]

        with open(path, "wb") as f:
            written = 0
            while written < size:
                to_write = min(self.block_size, size - written)
                f.write(block[:to_write])
                written += to_write

            f.flush()
            os.fsync(f.fileno())

    async def _write_random(self, path: Path, size: int) -> None:
        """Write random data to file."""
        with open(path, "wb") as f:
            written = 0
            while written < size:
                to_write = min(self.block_size, size - written)
                f.write(os.urandom(to_write))
                written += to_write

            f.flush()
            os.fsync(f.fileno())

    async def wipe_directory(
        self,
        path: Path,
        method: Optional[WipeMethod] = None,
        recursive: bool = True,
    ) -> list[WipeResult]:
        """
        Securely wipe all files in a directory.

        Args:
            path: Directory path
            method: Wipe method
            recursive: Process subdirectories

        Returns:
            List of WipeResult for each file
        """
        results = []

        if not path.exists():
            return results

        # Get all files
        if recursive:
            files = list(path.rglob("*"))
        else:
            files = list(path.glob("*"))

        # Wipe files (deepest first for proper directory removal)
        files.sort(key=lambda p: len(p.parts), reverse=True)

        for file_path in files:
            if file_path.is_file():
                result = await self.wipe_file(file_path, method)
                results.append(result)

        # Remove empty directories
        for dir_path in sorted(path.rglob("*"), reverse=True):
            if dir_path.is_dir():
                try:
                    dir_path.rmdir()
                except OSError:
                    pass

        # Remove root directory
        try:
            path.rmdir()
        except OSError:
            pass

        return results

    async def wipe_free_space(
        self,
        path: Path,
        method: WipeMethod = WipeMethod.RANDOM,
    ) -> WipeResult:
        """
        Wipe free space on filesystem.

        Creates temporary file to fill disk, then wipes it.

        Args:
            path: Path on target filesystem
            method: Wipe method

        Returns:
            WipeResult
        """
        temp_file = path / f".wipe_{secrets.token_hex(8)}"

        try:
            # Get available space
            stat = os.statvfs(path)
            available = stat.f_bavail * stat.f_frsize

            # Leave some margin (10MB)
            to_write = max(0, available - 10 * 1024 * 1024)

            if to_write == 0:
                return WipeResult(
                    path=str(path),
                    success=True,
                    bytes_wiped=0,
                    passes=0,
                )

            # Write random data to fill space
            logger.info(f"Wiping {to_write} bytes of free space on {path}")

            with open(temp_file, "wb") as f:
                written = 0
                while written < to_write:
                    try:
                        chunk = min(1024 * 1024, to_write - written)
                        f.write(os.urandom(chunk))
                        written += chunk
                    except OSError:
                        break  # Disk full

                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass

            # Wipe the temp file
            result = await self.wipe_file(temp_file, method)
            result.path = str(path)
            return result

        except Exception as e:
            # Clean up on error
            if temp_file.exists():
                temp_file.unlink()

            return WipeResult(
                path=str(path),
                success=False,
                bytes_wiped=0,
                passes=0,
                error=str(e),
            )

    async def quick_wipe(self, path: Path) -> bool:
        """
        Quick wipe - single pass random, no verification.

        Args:
            path: Path to wipe

        Returns:
            True if successful
        """
        if path.is_file():
            try:
                size = path.stat().st_size
                await self._write_random(path, size)
                path.unlink()
                return True
            except Exception:
                return False

        elif path.is_dir():
            results = await self.wipe_directory(path, WipeMethod.RANDOM)
            return all(r.success for r in results)

        return True

