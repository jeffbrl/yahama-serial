"""Mock Serial Driver for offline testing and development without hardware."""

import asyncio
import logging
from typing import Optional
from yamaha_serial.driver.base import BaseSerialDriver

logger = logging.getLogger(__name__)


class MockSerialDriver(BaseSerialDriver):
    def __init__(self):
        self._connected = False

    async def connect(self) -> None:
        await asyncio.sleep(0.05)
        self._connected = True
        logger.info("[MockSerialDriver] Connected to simulated RX-Z1 receiver.")

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("[MockSerialDriver] Disconnected from simulated RX-Z1 receiver.")

    def is_connected(self) -> bool:
        return self._connected

    async def send_command(self, data: bytes) -> Optional[bytes]:
        if not self._connected:
            raise ConnectionError("Mock serial driver is not connected.")
        
        # Simulate slight round-trip communication latency
        await asyncio.sleep(0.03)
        hex_repr = " ".join(f"{b:02X}" for b in data)
        ascii_repr = data.decode("ascii", errors="replace").strip()
        logger.info(f"[MockSerialDriver] Sent bytes: {hex_repr} ('{ascii_repr}')")

        # Simulate ACK response
        return b"\x06"
