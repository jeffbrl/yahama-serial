"""Yamaha RX-Z1 State Controller.

Coordinates receiver state, formats commands, and notifies subscribers.
"""

import asyncio
import logging
from typing import Callable, Set, Optional
from pydantic import BaseModel

from yamaha_serial.config import settings
from yamaha_serial.driver.base import BaseSerialDriver
from yamaha_serial.driver.hardware import HardwareSerialDriver
from yamaha_serial.driver.mock import MockSerialDriver
from yamaha_serial.protocol.commands import (
    PowerState,
    InputSource,
    DSPProgram,
    POWER_COMMAND_MAP,
    INPUT_COMMAND_MAP,
    VOLUME_COMMANDS,
    DSP_COMMAND_MAP,
    STATUS_POLL_COMMAND,
    encode_command,
    parse_serial_message,
    db_to_percent,
    percent_to_db,
)

logger = logging.getLogger("yamaha_serial.controller")


class ReceiverState(BaseModel):
    power: PowerState = PowerState.STANDBY
    volume_db: float = -40.0
    volume_percent: int = 50
    mute: bool = False
    input: InputSource = InputSource.CD
    dsp: DSPProgram = DSPProgram.SURROUND_STANDARD
    connected: bool = False
    mock_mode: bool = False


class YamahaController:
    def __init__(self, driver: BaseSerialDriver):
        self.driver = driver
        self.state = ReceiverState(
            mock_mode=isinstance(driver, MockSerialDriver)
        )
        self._listeners: Set[Callable[[ReceiverState], asyncio.Task]] = set()
        self._rx_buffer = bytearray()
        self._poll_task: Optional[asyncio.Task] = None

        # Connect driver callback to serial incoming bytes handler
        self.driver.set_data_callback(self._on_serial_data)

    def _on_serial_data(self, data: bytes) -> None:
        """Accumulate bytes and parse framed messages from RX-Z1."""
        logger.debug(f"Raw serial chunk received: {data}")
        self._rx_buffer.extend(data)

        # Process frames delimited by STX (0x02) and ETX (0x03) or CRLF
        while True:
            # Check for STX ... ETX frame
            stx_idx = self._rx_buffer.find(b"\x02")
            if stx_idx != -1:
                etx_idx = self._rx_buffer.find(b"\x03", stx_idx)
                if etx_idx != -1:
                    raw_frame = self._rx_buffer[stx_idx + 1:etx_idx].decode("ascii", errors="replace")
                    del self._rx_buffer[:etx_idx + 1]
                    asyncio.create_task(self._handle_incoming_frame(raw_frame))
                    continue

            # Check for CRLF delimiter
            crlf_idx = self._rx_buffer.find(b"\r")
            if crlf_idx != -1:
                raw_frame = self._rx_buffer[:crlf_idx].decode("ascii", errors="replace").strip("\x02\x03\n")
                del self._rx_buffer[:crlf_idx + 1]
                if self._rx_buffer.startswith(b"\n"):
                    del self._rx_buffer[:1]
                if raw_frame:
                    asyncio.create_task(self._handle_incoming_frame(raw_frame))
                continue

            # If buffer gets too large without delimiters, flush
            if len(self._rx_buffer) > 256:
                self._rx_buffer.clear()
            break

    async def _handle_incoming_frame(self, frame: str) -> None:
        """Apply parsed state updates and broadcast to WebSocket/clients."""
        logger.info(f"Incoming serial frame from receiver: {frame}")
        updates = parse_serial_message(frame)
        if not updates:
            logger.debug(f"Frame not recognized or ignored: {frame}")
            return

        changed = False
        if "power" in updates and self.state.power != updates["power"]:
            self.state.power = updates["power"]
            changed = True
            logger.info(f"State updated: power -> {self.state.power}")
        elif any(k in updates for k in ("input", "dsp", "volume_percent", "volume_step")) and self.state.power != PowerState.ON:
            # Active operational frames indicate the receiver is awake and running
            self.state.power = PowerState.ON
            changed = True
            logger.info(f"State updated: power -> {self.state.power} (inferred from operational feedback)")

        if "input" in updates and self.state.input != updates["input"]:
            self.state.input = updates["input"]
            changed = True
            logger.info(f"State updated: input -> {self.state.input}")
        if "dsp" in updates and self.state.dsp != updates["dsp"]:
            self.state.dsp = updates["dsp"]
            changed = True
            logger.info(f"State updated: dsp -> {self.state.dsp}")
        if "mute" in updates and self.state.mute != updates["mute"]:
            self.state.mute = updates["mute"]
            changed = True
            logger.info(f"State updated: mute -> {self.state.mute}")
        if "volume_percent" in updates and self.state.volume_percent != updates["volume_percent"]:
            self.state.volume_percent = updates["volume_percent"]
            self.state.volume_db = updates.get("volume_db", percent_to_db(self.state.volume_percent))
            changed = True
            logger.info(f"State updated: volume -> {self.state.volume_percent}% ({self.state.volume_db:.1f} dB)")
        if "volume_step" in updates:
            step = updates["volume_step"]
            if step == "UP":
                self.state.volume_percent = min(100, self.state.volume_percent + 2)
            elif step == "DOWN":
                self.state.volume_percent = max(0, self.state.volume_percent - 2)
            self.state.volume_db = percent_to_db(self.state.volume_percent)
            changed = True
            logger.info(f"State updated: volume -> {self.state.volume_percent}% ({self.state.volume_db:.1f} dB)")

        if changed:
            await self._broadcast_state()

    async def poll_status(self) -> None:
        """Query receiver for its current operational status report."""
        if self.driver.is_connected():
            logger.debug("Polling receiver status...")
            await self.send_raw_code(STATUS_POLL_COMMAND)

    async def _poll_loop(self) -> None:
        """Periodic background task to poll receiver state and keep status synchronized."""
        logger.info(f"Starting receiver status polling loop (interval={settings.POLL_INTERVAL}s)")
        while True:
            try:
                await asyncio.sleep(settings.POLL_INTERVAL)
                await self.poll_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error during status poll: {e}")

    async def start(self) -> None:
        try:
            logger.info("Initializing serial driver connection...")
            await self.driver.connect()
            self.state.connected = self.driver.is_connected()
            logger.info(f"Serial driver connection status: connected={self.state.connected}")
        except Exception as e:
            logger.warning(f"Could not connect driver on startup: {e}")
            self.state.connected = False

        if self.state.connected:
            try:
                await self.poll_status()
            except Exception as e:
                logger.debug(f"Initial status poll failed: {e}")

        if settings.ENABLE_POLLING:
            self._poll_task = asyncio.create_task(self._poll_loop())

        await self._broadcast_state()

    async def stop(self) -> None:
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        await self.driver.disconnect()
        self.state.connected = False
        await self._broadcast_state()

    def add_listener(self, listener: Callable[[ReceiverState], asyncio.Task]) -> None:
        self._listeners.add(listener)

    def remove_listener(self, listener: Callable[[ReceiverState], asyncio.Task]) -> None:
        self._listeners.discard(listener)

    async def _broadcast_state(self) -> None:
        for listener in list(self._listeners):
            try:
                res = listener(self.state)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Error calling state listener: {e}")

    async def send_raw_code(self, code: str) -> None:
        data = encode_command(code)
        await self.driver.send_command(data)

    async def set_power(self, power: PowerState) -> ReceiverState:
        if power == PowerState.TOGGLE:
            next_state = PowerState.STANDBY if self.state.power == PowerState.ON else PowerState.ON
        else:
            next_state = power

        code = POWER_COMMAND_MAP.get(power, "07EA0")
        await self.send_raw_code(code)
        # Yamaha AVRs in cold standby often need a secondary pulse to reliably wake
        if next_state == PowerState.ON:
            await asyncio.sleep(0.05)
            await self.send_raw_code(code)

        self.state.power = next_state
        await self._broadcast_state()
        return self.state

    async def set_volume_percent(self, percent: int) -> ReceiverState:
        percent = max(0, min(100, percent))
        self.state.volume_percent = percent
        self.state.volume_db = percent_to_db(percent)
        await self._broadcast_state()
        return self.state

    async def volume_up(self) -> ReceiverState:
        await self.send_raw_code(VOLUME_COMMANDS["UP"])
        new_pct = min(100, self.state.volume_percent + 2)
        return await self.set_volume_percent(new_pct)

    async def volume_down(self) -> ReceiverState:
        await self.send_raw_code(VOLUME_COMMANDS["DOWN"])
        new_pct = max(0, self.state.volume_percent - 2)
        return await self.set_volume_percent(new_pct)

    async def set_mute(self, mute: bool) -> ReceiverState:
        code = VOLUME_COMMANDS["MUTE_ON"] if mute else VOLUME_COMMANDS["MUTE_OFF"]
        await self.send_raw_code(code)
        self.state.mute = mute
        await self._broadcast_state()
        return self.state

    async def toggle_mute(self) -> ReceiverState:
        return await self.set_mute(not self.state.mute)

    async def set_input(self, source: InputSource) -> ReceiverState:
        code = INPUT_COMMAND_MAP.get(source)
        if code:
            await self.send_raw_code(code)
        self.state.input = source
        await self._broadcast_state()
        return self.state

    async def set_dsp(self, dsp: DSPProgram) -> ReceiverState:
        code = DSP_COMMAND_MAP.get(dsp)
        if code:
            await self.send_raw_code(code)
        self.state.dsp = dsp
        await self._broadcast_state()
        return self.state


def create_controller() -> YamahaController:
    if settings.MOCK_SERIAL:
        driver = MockSerialDriver()
    else:
        driver = HardwareSerialDriver(
            port=settings.SERIAL_PORT,
            baudrate=settings.SERIAL_BAUDRATE,
            timeout=settings.SERIAL_TIMEOUT,
        )
    return YamahaController(driver)
