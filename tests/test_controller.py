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
