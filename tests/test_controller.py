import pytest
import asyncio
from yamaha_serial.driver.mock import MockSerialDriver
from yamaha_serial.controller import YamahaController
from yamaha_serial.protocol.commands import PowerState, InputSource, DSPProgram, encode_command, db_to_percent, percent_to_db


@pytest.mark.asyncio
async def test_driver_and_controller_flow():
    driver = MockSerialDriver()
    controller = YamahaController(driver)
    await controller.start()

    assert controller.state.connected is True
    assert controller.state.mock_mode is True

    # Test Power
    await controller.set_power(PowerState.ON)
    assert controller.state.power == PowerState.ON

    # Test Volume
    await controller.set_volume_percent(75)
    assert controller.state.volume_percent == 75
    assert controller.state.volume_db == percent_to_db(75)

    await controller.volume_up()
    assert controller.state.volume_percent == 77

    await controller.volume_down()
    assert controller.state.volume_percent == 75

    # Test Mute
    await controller.set_mute(True)
    assert controller.state.mute is True
    await controller.toggle_mute()
    assert controller.state.mute is False

    # Test Input
    await controller.set_input(InputSource.DVD)
    assert controller.state.input == InputSource.DVD

    # Test DSP
    await controller.set_dsp(DSPProgram.SPECTACULAR)
    assert controller.state.dsp == DSPProgram.SPECTACULAR

    await controller.stop()
    assert controller.state.connected is False


def test_command_encoding():
    frame = encode_command("07EA2", use_framing=True)
    assert frame == b"\x0207EA2\x03"

    frame_crlf = encode_command("07EA2", use_framing=False)
    assert frame_crlf == b"07EA2\r\n"


def test_db_conversions():
    assert db_to_percent(-80.0) == 0
    assert db_to_percent(0.0) == 100
    assert db_to_percent(-40.0) == 50
    assert percent_to_db(0) == -80.0
    assert percent_to_db(100) == 0.0
    assert percent_to_db(50) == -40.0

from fastapi.testclient import TestClient
from yamaha_serial.main import app

def test_api_endpoints():
    with TestClient(app) as client:
        # State
        res = client.get("/api/state")
        assert res.status_code == 200
        data = res.json()
        assert "power" in data
        assert "volume_db" in data
        assert "input" in data

        # Power
        res = client.post("/api/power", json={"power": "ON"})
        assert res.status_code == 200
        assert res.json()["power"] == "ON"

        # Volume
        res = client.post("/api/volume/percent", json={"percent": 60})
        assert res.status_code == 200
        assert res.json()["volume_percent"] == 60

        # Input
        res = client.post("/api/input", json={"source": "PHONO"})
        assert res.status_code == 200
        assert res.json()["input"] == "PHONO"

        # DSP
        res = client.post("/api/dsp", json={"dsp": "2ch Stereo"})
        assert res.status_code == 200
        assert res.json()["dsp"] == "2ch Stereo"

        # Web UI
        res = client.get("/")
        assert res.status_code == 200
        assert "Yamaha RX-Z1 Controller" in res.text

def test_config_search_precedence(monkeypatch, tmp_path):
    from yamaha_serial.config import find_config_file
    
    # Test explicit override
    test_conf = tmp_path / "custom.conf"
    test_conf.write_text("MOCK_SERIAL=true\n")
    monkeypatch.setenv("YAMAHA_CONFIG_FILE", str(test_conf))
    assert find_config_file() == str(test_conf)

@pytest.mark.asyncio
async def test_unsolicited_incoming_serial_frames():
    driver = MockSerialDriver()
    controller = YamahaController(driver)
    await controller.start()

    # Test incoming power update from physical remote / front panel
    driver.simulate_incoming(b"\x0207E7E\x03")
    await asyncio.sleep(0.05)
    assert controller.state.power == PowerState.ON

    # Test incoming input update (e.g. user selected DVD on front panel)
    driver.simulate_incoming(b"\x0207EC1\x03")
    await asyncio.sleep(0.05)
    assert controller.state.input == InputSource.DVD

    # Test incoming mute update
    driver.simulate_incoming(b"\x0207EA7\x03")
    await asyncio.sleep(0.05)
    assert controller.state.mute is True

    # Test incoming volume step
    prev_vol = controller.state.volume_percent
    driver.simulate_incoming(b"\x0207ED0\x03")
    await asyncio.sleep(0.05)
    assert controller.state.volume_percent == prev_vol + 2

    await controller.stop()

def test_rx_z1_real_unsolicited_frames():
    from yamaha_serial.protocol.commands import parse_serial_message, InputSource, PowerState
    
    assert parse_serial_message("102100") == {"input": InputSource.PHONO}
    assert parse_serial_message("102101") == {"input": InputSource.CD}
    assert parse_serial_message("102102") == {"input": InputSource.TUNER}
    assert parse_serial_message("102105") == {"input": InputSource.DVD}
    assert parse_serial_message("102001") == {"power": PowerState.ON}
    assert parse_serial_message("102000") == {"power": PowerState.STANDBY}
    # 3010xx power status frames from RX-Z1 burst feedback
    assert parse_serial_message("301001") == {"power": PowerState.ON}
    assert parse_serial_message("301000") == {"power": PowerState.STANDBY}
    assert parse_serial_message("101001") == {"power": PowerState.ON}
    assert parse_serial_message("101000") == {"power": PowerState.STANDBY}
    assert parse_serial_message("01001") == {"power": PowerState.ON}
    assert parse_serial_message("01000") == {"power": PowerState.STANDBY}
    assert parse_serial_message("102200") == {"mute": False}
    assert parse_serial_message("102205") == {"mute": True}
    # 4026xx inputs
    assert parse_serial_message("402600") == {"input": InputSource.PHONO}
    assert parse_serial_message("402621") == {"input": InputSource.CD}
    assert parse_serial_message("402622") == {"input": InputSource.TUNER}
    assert parse_serial_message("402624") == {"input": InputSource.CD_R}
    assert parse_serial_message("402625") == {"input": InputSource.MD_TAPE}
    assert parse_serial_message("402605") == {"input": InputSource.DVD}
    assert parse_serial_message("402604") == {"input": InputSource.CD_R}
    assert parse_serial_message("40260F") == {"input": InputSource.VCR_1}
    assert parse_serial_message("402629") == {"input": InputSource.VCR_2}
    assert parse_serial_message("40260B") == {"input": InputSource.V_AUX}
    # 4028xx / 028xx volume frames
    vol_res = parse_serial_message("402814")
    assert "volume_percent" in vol_res
    assert "volume_db" in vol_res
    vol_res_short = parse_serial_message("0280C")
    assert "volume_percent" in vol_res_short


@pytest.mark.asyncio
async def test_volume_frame_updates_controller():
    driver = MockSerialDriver()
    controller = YamahaController(driver)
    await controller.start()

    # Simulate physical volume knob turn on receiver sending 402814
    driver.simulate_incoming(b"\x02402814\x03")
    await asyncio.sleep(0.05)
    # 0x14 = 20 -> 20/160 * 100 = 12%
    assert controller.state.volume_percent == 12

    # Simulate 402622 (TUNER selected on receiver front panel)
    driver.simulate_incoming(b"\x02402622\x03")
    await asyncio.sleep(0.05)
    assert controller.state.input == InputSource.TUNER

    await controller.stop()


@pytest.mark.asyncio
async def test_power_frame_updates_controller():
    driver = MockSerialDriver()
    controller = YamahaController(driver)
    await controller.start()

    assert controller.state.power == PowerState.STANDBY

    # Simulate receiver sending 301001 (unsolicited power ON report)
    driver.simulate_incoming(b"\x02301001\x03")
    await asyncio.sleep(0.05)
    assert controller.state.power == PowerState.ON

    # Simulate receiver sending 301000 (power STANDBY report)
    driver.simulate_incoming(b"\x02301000\x03")
    await asyncio.sleep(0.05)
    assert controller.state.power == PowerState.STANDBY

    # Simulate active input report arriving while in STANDBY (e.g. receiver turned on by input knob)
    driver.simulate_incoming(b"\x02402102\x03")
    await asyncio.sleep(0.05)
    assert controller.state.input == InputSource.TUNER
    assert controller.state.power == PowerState.ON
    await controller.stop()



@pytest.mark.asyncio
async def test_status_polling_updates_power(monkeypatch):
    from yamaha_serial.config import settings

    monkeypatch.setattr(settings, "ENABLE_POLLING", True)
    monkeypatch.setattr(settings, "POLL_INTERVAL", 0.05)

    driver = MockSerialDriver()
    controller = YamahaController(driver)
    await controller.start()

    assert controller.state.power == PowerState.STANDBY

    # Receiver power state changes externally (e.g. physical button or IR remote)
    driver._simulated_power = "01"

    # Wait for periodic poll to trigger and synchronize state
    await asyncio.sleep(0.12)
    assert controller.state.power == PowerState.ON

    # Receiver power state changes back to standby externally
    driver._simulated_power = "00"
    await asyncio.sleep(0.12)
    assert controller.state.power == PowerState.STANDBY

    await controller.stop()
    assert controller._poll_task is None


@pytest.mark.asyncio
async def test_polling_disabled(monkeypatch):
    from yamaha_serial.config import settings

    monkeypatch.setattr(settings, "ENABLE_POLLING", False)

    driver = MockSerialDriver()
    controller = YamahaController(driver)
    await controller.start()

    assert controller._poll_task is None
    await controller.stop()


