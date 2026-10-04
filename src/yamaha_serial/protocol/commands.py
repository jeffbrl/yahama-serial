"""Yamaha RX-Z1 RS-232 Serial Protocol Definitions, Encoders, and Parsers."""

from enum import Enum
from typing import Optional, Dict, Any


class PowerState(str, Enum):
    ON = "ON"
    STANDBY = "STANDBY"
    TOGGLE = "TOGGLE"


class InputSource(str, Enum):
    PHONO = "PHONO"
    CD = "CD"
    TUNER = "TUNER"
    MD_TAPE = "MD/TAPE"
    CD_R = "CD-R"
    DVD = "DVD"
    D_TV = "D-TV"
    CBL_SAT = "CBL/SAT"
    VCR_1 = "VCR 1"
    VCR_2 = "VCR 2"
    VCR_3 = "VCR 3/DVR"
    V_AUX = "V-AUX"


class DSPProgram(str, Enum):
    STEREO_2CH = "2ch Stereo"
    DIRECT = "Direct"
    CONCERT_HALL_1 = "Concert Hall 1"
    CONCERT_HALL_2 = "Concert Hall 2"
    CHURCH = "Church"
    JAZZ_CLUB = "Jazz Club"
    ROCK_CONCERT = "Rock Concert"
    ENTERTAINMENT = "Entertainment"
    MUSIC_VIDEO = "Music Video"
    SPECTACULAR = "70mm Spectacular"
    SCI_FI = "70mm Sci-Fi"
    ADVENTURE = "70mm Adventure"
    GENERAL = "70mm General"
    ENHANCED = "Enhanced"
    SURROUND_STANDARD = "Surround Standard"


# Forward transmit command codes
INPUT_COMMAND_MAP = {
    InputSource.PHONO: "07EA1",
    InputSource.CD: "07EA2",
    InputSource.TUNER: "07EA3",
    InputSource.MD_TAPE: "07EA4",
    InputSource.CD_R: "07EA5",
    InputSource.DVD: "07EC1",
    InputSource.D_TV: "07EC2",
    InputSource.CBL_SAT: "07EC3",
    InputSource.VCR_1: "07EC4",
    InputSource.VCR_2: "07EC5",
    InputSource.VCR_3: "07EC6",
    InputSource.V_AUX: "07EC7",
}

POWER_COMMAND_MAP = {
    PowerState.ON: "07E7E",
    PowerState.STANDBY: "07E7F",
    PowerState.TOGGLE: "07EA0",
}

VOLUME_COMMANDS = {
    "UP": "07ED0",
    "DOWN": "07ED1",
    "MUTE_ON": "07EA7",
    "MUTE_OFF": "07EA8",
    "MUTE_TOGGLE": "07EA6",
}

DSP_COMMAND_MAP = {
    DSPProgram.DIRECT: "07EB0",
    DSPProgram.STEREO_2CH: "07EB1",
    DSPProgram.SURROUND_STANDARD: "07EB2",
    DSPProgram.SPECTACULAR: "07EB3",
    DSPProgram.SCI_FI: "07EB4",
    DSPProgram.ADVENTURE: "07EB5",
    DSPProgram.GENERAL: "07EB6",
    DSPProgram.ENHANCED: "07EB7",
    DSPProgram.CONCERT_HALL_1: "07EB8",
    DSPProgram.CONCERT_HALL_2: "07EB9",
    DSPProgram.JAZZ_CLUB: "07EBA",
    DSPProgram.ROCK_CONCERT: "07EBB",
}

# Real RX-Z1 unsolicited feedback status codes
# 4021xx / 1021xx / 021xx: Main Zone Input
RX_Z1_INPUT_4021 = {
    "00": InputSource.PHONO,
    "01": InputSource.CD,
    "02": InputSource.TUNER,
    "03": InputSource.MD_TAPE,
    "04": InputSource.CD_R,
    "05": InputSource.DVD,
    "06": InputSource.D_TV,
    "07": InputSource.CBL_SAT,
    "08": InputSource.VCR_1,
    "09": InputSource.VCR_2,
    "0A": InputSource.VCR_3,
    "0B": InputSource.V_AUX,
}

# 4026xx / 1026xx / 026xx: Physical input knob / function bank
# On the RX-Z1 front panel rotary selector:
# 24 is CD-R, 25 is MD/TAPE (or vice versa in alternate numbering), 21 is CD, 22 is TUNER,
# 00 is PHONO, 05 is DVD, 0F is VCR 1, 29 is VCR 2, 0B is V-AUX
RX_Z1_INPUT_4026 = {
    "00": InputSource.PHONO,
    "21": InputSource.CD,
    "22": InputSource.TUNER,
    "24": InputSource.CD_R,
    "25": InputSource.MD_TAPE,
    "03": InputSource.MD_TAPE,
    "04": InputSource.CD_R,
    "05": InputSource.DVD,
    "06": InputSource.D_TV,
    "07": InputSource.CBL_SAT,
    "08": InputSource.VCR_1,
    "0F": InputSource.VCR_1,
    "09": InputSource.VCR_2,
    "29": InputSource.VCR_2,
    "0A": InputSource.VCR_3,
    "0B": InputSource.V_AUX,
}

# Reverse maps for command reflection
CODE_TO_INPUT = {v: k for k, v in INPUT_COMMAND_MAP.items()}
CODE_TO_POWER = {
    "07E7E": PowerState.ON,
    "07E7F": PowerState.STANDBY,
    "102001": PowerState.ON,
    "102000": PowerState.STANDBY,
    "402001": PowerState.ON,
    "402000": PowerState.STANDBY,
}
CODE_TO_DSP = {v: k for k, v in DSP_COMMAND_MAP.items()}


def encode_command(code: str, use_framing: bool = True) -> bytes:
    """Frame an RX-Z1 command with STX (0x02) and ETX (0x03) or CR/LF."""
    if use_framing:
        return b"\x02" + code.encode("ascii") + b"\x03"
    return (code + "\r\n").encode("ascii")


def db_to_percent(db: float) -> int:
    """Convert volume dB (-80.0 dB to 0.0 dB) to percentage 0-100%."""
    clamped = max(-80.0, min(0.0, db))
    return int(round(((clamped - (-80.0)) / 80.0) * 100))


def percent_to_db(percent: int) -> float:
    """Convert percentage 0-100% to volume dB (-80.0 dB to 0.0 dB)."""
    clamped = max(0, min(100, percent))
    return -80.0 + (clamped / 100.0) * 80.0


def parse_serial_message(raw_msg: str) -> Dict[str, Any]:
    """Parse incoming ASCII frame from RX-Z1.
    
    The Yamaha RX-Z1 report frames:
      - 4021xx or 1021xx: Main Zone Input (00=PHONO, 01=CD, 02=TUNER, 05=DVD, ...)
      - 4020xx or 1020xx: Main Zone Power (01=ON, 00=STANDBY)
      - 4022xx or 1022xx: Mute state (00=MUTE OFF, other=MUTE ON)
      - 4028xx or 1028xx: Master Volume Level in hex steps
      - 07Exxx: Command echo
    """
    clean = raw_msg.strip("\x02\x03\r\n ").upper()
    updates: Dict[str, Any] = {}

    if not clean:
        return updates

    # RX-Z1 Input Frame: 4021xx / 1021xx or 021xx (Main Zone Input)
    if (clean.startswith("4021") or clean.startswith("1021")) and len(clean) == 6:
        sub = clean[4:6]
        if sub in RX_Z1_INPUT_4021:
            updates["input"] = RX_Z1_INPUT_4021[sub]
            return updates
    elif clean.startswith("021") and len(clean) == 5:
        sub = clean[3:5]
        if sub in RX_Z1_INPUT_4021:
            updates["input"] = RX_Z1_INPUT_4021[sub]
            return updates

    # RX-Z1 Input Knob / Function Bank Frame: 4026xx / 1026xx or 026xx
    if (clean.startswith("4026") or clean.startswith("1026")) and len(clean) == 6:
        sub = clean[4:6]
        if sub in RX_Z1_INPUT_4026:
            updates["input"] = RX_Z1_INPUT_4026[sub]
            return updates
    elif clean.startswith("026") and len(clean) == 5:
        sub = clean[3:5]
        if sub in RX_Z1_INPUT_4026:
            updates["input"] = RX_Z1_INPUT_4026[sub]
            return updates

    # RX-Z1 Power Frame: 4020xx or 1020xx or 020xx
    if (clean.startswith("4020") or clean.startswith("1020")) and len(clean) == 6:
        pwr_code = clean[4:6]
        updates["power"] = PowerState.ON if pwr_code == "01" else PowerState.STANDBY
        return updates
    elif clean.startswith("020") and len(clean) == 5:
        pwr_code = clean[3:5]
        updates["power"] = PowerState.ON if pwr_code == "01" else PowerState.STANDBY
        return updates

    # RX-Z1 Mute Frame: 4022xx or 1022xx or 022xx
    # 00 = Mute Off, non-zero (e.g. 05) = Mute On / Attenuate
    if (clean.startswith("4022") or clean.startswith("1022")) and len(clean) == 6:
        mute_code = clean[4:6]
        updates["mute"] = (mute_code != "00")
        return updates
    elif clean.startswith("022") and len(clean) == 5:
        mute_code = clean[3:5]
        updates["mute"] = (mute_code != "00")
        return updates

    # RX-Z1 Volume Frame: 4028xx or 1028xx or 028xx (Hex volume level)
    if (clean.startswith("4028") or clean.startswith("1028")) and len(clean) == 6:
        try:
            vol_hex = clean[4:6]
            vol_int = int(vol_hex, 16)
            updates["volume_percent"] = min(100, max(0, int((vol_int / 160.0) * 100)))
            updates["volume_db"] = percent_to_db(updates["volume_percent"])
            return updates
        except ValueError:
            pass
    elif clean.startswith("028") and len(clean) == 5:
        try:
            vol_hex = clean[3:5]
            vol_int = int(vol_hex, 16)
            updates["volume_percent"] = min(100, max(0, int((vol_int / 160.0) * 100)))
            updates["volume_db"] = percent_to_db(updates["volume_percent"])
            return updates
        except ValueError:
            pass

    # Check Power reflection
    if clean in CODE_TO_POWER:
        updates["power"] = CODE_TO_POWER[clean]
        return updates

    # Check Input reflection
    if clean in CODE_TO_INPUT:
        updates["input"] = CODE_TO_INPUT[clean]
        return updates

    # Check DSP
    if clean in CODE_TO_DSP:
        updates["dsp"] = CODE_TO_DSP[clean]
        return updates

    # Check Mute reflection
    if clean == VOLUME_COMMANDS["MUTE_ON"]:
        updates["mute"] = True
        return updates
    elif clean == VOLUME_COMMANDS["MUTE_OFF"]:
        updates["mute"] = False
        return updates

    # Check Volume relative steps
    if clean == VOLUME_COMMANDS["UP"]:
        updates["volume_step"] = "UP"
        return updates
    elif clean == VOLUME_COMMANDS["DOWN"]:
        updates["volume_step"] = "DOWN"
        return updates

    return updates
