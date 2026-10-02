"""Yamaha RX-Z1 State Controller.

Coordinates receiver state, formats commands, and notifies subscribers.
"""

import asyncio
import logging
from typing import Callable, Set
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
    encode_command,
    db_to_percent,
    percent_to_db,
)

logger = logging.getLogger(__name__)


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

    async def start(self) -> None:
        try:
            await self.driver.connect()
            self.state.connected = self.driver.is_connected()
        except Exception as e:
            logger.warning(f"Could not connect driver on startup: {e}")
            self.state.connected = False
        await self._broadcast_state()

    async def stop(self) -> None:
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
        self.state.power = next_state
        await self._broadcast_state()
        return self.state

    async def set_volume_percent(self, percent: int) -> ReceiverState:
        percent = max(0, min(100, percent))
        self.state.volume_percent = percent
        self.state.volume_db = percent_to_db(percent)
        # Note: Yamaha RX-Z1 supports direct volume codes or step commands
        # For precision, we send step adjustments or the direct parameter frame
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
