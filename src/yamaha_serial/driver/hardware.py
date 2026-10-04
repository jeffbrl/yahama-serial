"""Hardware Serial Driver using pyserial-asyncio for physical RS-232 communication."""

import asyncio
import logging
from typing import Optional, Callable
import serial
import serial_asyncio

from yamaha_serial.driver.base import BaseSerialDriver

logger = logging.getLogger(__name__)


class RXProtocol(asyncio.Protocol):
    """Protocol handler for incoming RS-232 serial bytes."""

    def __init__(self, driver: "HardwareSerialDriver"):
        self.driver = driver
        self.transport: Optional[asyncio.Transport] = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"Serial connection established on {self.driver.port}")

    def data_received(self, data: bytes):
        if self.driver.data_callback:
            try:
                self.driver.data_callback(data)
            except Exception as e:
                logger.error(f"Error in serial data_callback: {e}")

    def connection_lost(self, exc):
        logger.warning(f"Serial connection lost on {self.driver.port}: {exc}")
        self.driver._connected = False


class HardwareSerialDriver(BaseSerialDriver):
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.transport: Optional[asyncio.Transport] = None
        self.protocol: Optional[RXProtocol] = None
        self.data_callback: Optional[Callable[[bytes], None]] = None
        self._connected = False
        self._lock = asyncio.Lock()

    def set_data_callback(self, callback: Optional[Callable[[bytes], None]]) -> None:
        self.data_callback = callback

    async def connect(self) -> None:
        async with self._lock:
            if self.is_connected():
                return
            logger.info(f"Connecting to hardware serial port: {self.port} @ {self.baudrate} 8N1")
            try:
                loop = asyncio.get_running_loop()
                self.transport, self.protocol = await serial_asyncio.create_serial_connection(
                    loop,
                    lambda: RXProtocol(self),
                    url=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=self.timeout,
                )
                self._connected = True
                logger.info(f"Successfully opened serial port {self.port}")
            except Exception as e:
                self._connected = False
                logger.error(f"Failed to open serial port {self.port}: {e}")
                raise

    async def disconnect(self) -> None:
        async with self._lock:
            if self.transport:
                self.transport.close()
            self.transport = None
            self.protocol = None
            self._connected = False
            logger.info(f"Closed serial port {self.port}")

    def is_connected(self) -> bool:
        return self._connected and self.transport is not None

    async def send_command(self, data: bytes) -> Optional[bytes]:
        async with self._lock:
            if not self.is_connected() or not self.transport:
                raise ConnectionError(f"Serial port {self.port} is not connected.")

            hex_repr = " ".join(f"{b:02X}" for b in data)
            ascii_repr = data.decode("ascii", errors="replace").strip()
            logger.info(f"Writing to serial {self.port}: {hex_repr} ('{ascii_repr}')")

            self.transport.write(data)
            return None
