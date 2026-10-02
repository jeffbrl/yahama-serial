"""Hardware Serial Driver using pyserial-asyncio for physical RS-232 communication."""

import asyncio
import logging
from typing import Optional
import serial
import serial_asyncio

from yamaha_serial.driver.base import BaseSerialDriver

logger = logging.getLogger(__name__)


class HardwareSerialDriver(BaseSerialDriver):
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self.is_connected():
                return
            logger.info(f"Connecting to hardware serial port: {self.port} @ {self.baudrate} 8N1")
            try:
                self.reader, self.writer = await serial_asyncio.open_serial_connection(
                    url=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                )
                logger.info(f"Successfully opened serial port {self.port}")
            except Exception as e:
                logger.error(f"Failed to open serial port {self.port}: {e}")
                raise

    async def disconnect(self) -> None:
        async with self._lock:
            if self.writer:
                self.writer.close()
                try:
                    await self.writer.wait_closed()
                except Exception:
                    pass
            self.reader = None
            self.writer = None
            logger.info(f"Closed serial port {self.port}")

    def is_connected(self) -> bool:
        return self.writer is not None and not self.writer.is_closing()

    async def send_command(self, data: bytes) -> Optional[bytes]:
        async with self._lock:
            if not self.is_connected():
                raise ConnectionError(f"Serial port {self.port} is not connected.")

            self.writer.write(data)
            await self.writer.drain()

            # Read response with timeout
            try:
                if self.reader:
                    response = await asyncio.wait_for(self.reader.read(64), timeout=self.timeout)
                    return response
            except asyncio.TimeoutError:
                logger.debug(f"Command timed out waiting for response from {self.port}")
                return None
        return None
