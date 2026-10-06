"""Mock Serial Driver for offline testing and development without hardware."""

import asyncio
import logging
from typing import Optional, Callable
from yamaha_serial.driver.base import BaseSerialDriver

logger = logging.getLogger(__name__)


class MockSerialDriver(BaseSerialDriver):
    def __init__(self):
        self._connected = False
        self._callback: Optional[Callable[[bytes], None]] = None
        self._simulated_power: str = "00"

    async def connect(self) -> None:
        await asyncio.sleep(0.05)
        self._connected = True
        logger.info("[MockSerialDriver] Connected to simulated RX-Z1 receiver.")

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("[MockSerialDriver] Disconnected from simulated RX-Z1 receiver.")

    def is_connected(self) -> bool:
        return self._connected

    def set_data_callback(self, callback: Optional[Callable[[bytes], None]]) -> None:
        self._callback = callback

    async def send_command(self, data: bytes) -> Optional[bytes]:
        if not self._connected:
            raise ConnectionError("Mock serial driver is not connected.")
        
        await asyncio.sleep(0.03)
        hex_repr = " ".join(f"{b:02X}" for b in data)
        ascii_repr = data.decode("ascii", errors="replace").strip()
        logger.info(f"[MockSerialDriver] Sent bytes: {hex_repr} ('{ascii_repr}')")

        raw_str = data.strip(b"\x02\x03\r\n ").decode("ascii", errors="replace")
        if "07E7E" in raw_str:
            self._simulated_power = "01"
        elif "07E7F" in raw_str:
            self._simulated_power = "00"
        elif "20000" in raw_str and self._callback:
            self._callback(b"\x023010" + self._simulated_power.encode("ascii") + b"\x03")

        return b"\x06"

    def simulate_incoming(self, data: bytes) -> None:
        """Helper to test unsolicited incoming serial frames from the receiver."""
        if self._callback:
            self._callback(data)

