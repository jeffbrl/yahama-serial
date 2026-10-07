"""Configuration settings for Yamaha RX-Z1 Serial Controller."""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def find_config_file() -> Optional[str]:
    """Search standard Linux and local paths for configuration file.
    
    Precedence:
    1. YAMAHA_CONFIG_FILE environment variable (explicit override)
    2. /etc/yamaha-serial/config.env or /etc/yamaha-serial/yamaha-serial.conf
    3. ~/.config/yamaha-serial/config.env
    4. .env in current working directory
    5. .env in executable/project directory
    """
    explicit = os.environ.get("YAMAHA_CONFIG_FILE")
    if explicit and Path(explicit).is_file():
        return explicit

    # Project root directory
    app_dir = Path(__file__).resolve().parent.parent.parent

    home_config = Path.home() / ".config" / "yamaha-serial"

    candidates = [
        Path("/etc/yamaha-serial/config.env"),
        Path("/etc/yamaha-serial/yamaha-serial.conf"),
        Path("/etc/yamaha-serial.conf"),
        home_config / "config.env",
        home_config / "yamaha-serial.conf",
        Path.cwd() / "config.env",
        Path.cwd() / ".env",
        app_dir / "config.env",
        app_dir / ".env",
    ]

    for path in candidates:
        try:
            if path.is_file():
                return str(path)
        except OSError:
            continue

    return None


CONFIG_FILE_PATH = find_config_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=CONFIG_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Path to loaded config file (if any)
    CONFIG_PATH: Optional[str] = CONFIG_FILE_PATH

    # Serial Port Settings
    SERIAL_PORT: str = "/dev/ttyUSB0"
    SERIAL_BAUDRATE: int = 9600
    SERIAL_TIMEOUT: float = 1.0

    # Operation Mode: True simulates serial hardware without physical device
    MOCK_SERIAL: bool = True

    # Status Polling Settings
    ENABLE_POLLING: bool = True
    POLL_INTERVAL: float = 10.0

    # Web Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"
    RELOAD: bool = False




settings = Settings()
