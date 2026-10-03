"""Configuration settings for Yamaha RX-Z1 Serial Controller."""

import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine directory where the binary or script is located
if getattr(sys, "frozen", False):
    # Running in a PyInstaller bundle -> directory of the executable
    APP_DIR = Path(sys.executable).resolve().parent
else:
    # Running in normal Python -> project root directory
    APP_DIR = Path(__file__).resolve().parent.parent.parent

# Check for .env in current working directory first, fallback to executable directory
CWD_ENV = Path.cwd() / ".env"
EXE_ENV = APP_DIR / ".env"

if CWD_ENV.exists():
    ENV_FILE_PATH = str(CWD_ENV)
elif EXE_ENV.exists():
    ENV_FILE_PATH = str(EXE_ENV)
else:
    ENV_FILE_PATH = ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_file_encoding="utf-8", extra="ignore")

    # Serial Port Settings
    SERIAL_PORT: str = "/dev/ttyUSB0"
    SERIAL_BAUDRATE: int = 9600
    SERIAL_TIMEOUT: float = 1.0

    # Operation Mode: True simulates serial hardware without physical device
    MOCK_SERIAL: bool = True

    # Web Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"


settings = Settings()
