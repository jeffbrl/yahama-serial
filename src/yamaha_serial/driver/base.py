"""Abstract base class for Serial communication."""

import abc
from typing import Optional, Callable


class BaseSerialDriver(abc.ABC):
    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish serial connection."""
        pass

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Close serial connection."""
        pass

    @abc.abstractmethod
    async def send_command(self, data: bytes) -> Optional[bytes]:
        """Send raw bytes and optionally await response."""
        pass

    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Return True if connection is active."""
        pass

    @abc.abstractmethod
    def set_data_callback(self, callback: Optional[Callable[[bytes], None]]) -> None:
        """Set callback invoked whenever incoming bytes arrive from receiver."""
        pass
