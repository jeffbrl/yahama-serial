"""Yamaha RX-Z1 RS-232 Serial Protocol Definitions and Encoders.

The Yamaha RX-Z1 supports two serial control formats:
1. Standard ASCII Commands / Codes (e.g. \x0207EA2\x03 format or ASCII command strings)
2. Yamaha RS-232C Extended Command Set

This module encapsulates command codes, volume conversions (dB <-> percentage <-> raw bytes),
and message framing with STX (0x02) and ETX (0x03) delimiters.
"""

from enum import Enum
from typing import Optional


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


# Mapping friendly source to RX-Z1 command codes
# RX-Z1 command codes are typically 7-character or ASCII hex sequences
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


def encode_command(code: str, use_framing: bool = True) -> bytes:
    """Frame an RX-Z1 command with STX (0x02) and ETX (0x03) or CR/LF."""
    if use_framing:
        # Standard Yamaha controller frame: STX + Command + ETX
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
