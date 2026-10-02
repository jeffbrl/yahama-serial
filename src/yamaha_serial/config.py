"""Configuration settings for Yamaha RX-Z1 Serial Controller."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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
