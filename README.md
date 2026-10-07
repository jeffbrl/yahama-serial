# Yamaha RX-Z1 Serial Controller

A portable, modern Python application to monitor and control the flagship **Yamaha RX-Z1 AV Receiver** via RS-232 serial. 

Engineered to run seamlessly on a **Raspberry Pi** connected to the receiver via USB-to-Serial, while remaining 100% portable across Linux, macOS, and Windows. It provides a clean REST API, real-time WebSocket state broadcasting, and a responsive web UI.

---

## Features

- **Portable RS-232 Driver**: Built on `pyserial-asyncio` for non-blocking serial communication.
- **Hardware Simulator / Mock Mode**: Full offline simulation mode (`MOCK_SERIAL=true`) allows UI and API development without needing physical hardware connected.
- **REST API**: Complete endpoints to control power, volume, input selection, muting, and Cinema DSP modes, plus a raw command passthrough.
- **Real-Time State Push (WebSockets)**: Bi-directional WebSocket endpoint (`/api/ws`) pushes receiver state updates immediately to all connected browsers or clients.
- **Responsive Web UI**: Modern, dark-mode audio gear interface built with Tailwind CSS. Optimized for mobile phone screens, tablets, and desktop browsers.
- **Raspberry Pi Ready**: Includes systemd unit file and udev configuration guide for plug-and-play boot persistence.
- **Interactive Documentation**: Interactive OpenAPI/Swagger documentation available at `/docs`.

---

## Receiver Hardware & Serial Specifications

### RS-232 Port Settings
| Parameter | Value |
| :--- | :--- |
| **Baud Rate** | `9600 bps` |
| **Data Bits** | `8` |
| **Parity** | `None` |
| **Stop Bits** | `1` |
| **Flow Control** | `None` |
| **Cable** | Standard 9-pin RS-232 Null-Modem cable (pins 2-Rx, 3-Tx, 5-GND) or USB-to-RS232 adapter |

### Protocol Framing
Commands sent to the receiver use standard Yamaha framing:
- **STX** (`0x02`) + ASCII Command Code + **ETX** (`0x03`)
- Example: Power ON code is `07E7E` -> framed as `\x0207E7E\x03`.

---

## Architecture Overview

```
               ┌─────────────────────────────────────────┐
               │         Browser Web UI (Mobile/PC)      │
               └────────────────────┬────────────────────┘
                                    │ HTTP / WebSocket
                                    ▼
               ┌─────────────────────────────────────────┐
               │           FastAPI Web Server            │
               │   - REST Endpoints (/api/power, etc.)   │
               │   - WebSocket Broadcaster (/api/ws)     │
               └────────────────────┬────────────────────┘
                                    │
               ┌────────────────────▼────────────────────┐
               │       YamahaController State Machine     │
               └────────────────────┬────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
        (MOCK_SERIAL=false)                 (MOCK_SERIAL=true)
                    ▼                               ▼
       ┌────────────────────────┐       ┌───────────────────────┐
       │  HardwareSerialDriver  │       │   MockSerialDriver    │
       │ (pyserial-asyncio)     │       │ (Offline Simulator)   │
       └────────────┬───────────┘       └───────────────────────┘
                    │
            /dev/ttyUSB0 (9600 8N1)
                    ▼
       ┌────────────────────────┐
       │  Yamaha RX-Z1 Receiver │
       └────────────────────────┘
```

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- (Optional) USB-to-RS232 DB9 adapter (e.g. FTDI or Prolific chipset) connected to the RX-Z1 RS-232 port.

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/jeffbrl/yahama-serial.git
cd yahama-serial

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

To install development dependencies (testing):
```bash
pip install -e ".[dev]"
```

### 3. Configuration
The application is configured through environment variables or a `.env` file:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MOCK_SERIAL` | `true` | When `true`, simulates receiver responses without physical hardware. Set to `false` for live use. |
| `SERIAL_PORT` | `/dev/ttyUSB0` | Serial device path (e.g. `/dev/ttyUSB0` on Linux, `COM3` on Windows). |
| `SERIAL_BAUDRATE` | `9600` | Baud rate for the RX-Z1 serial interface. |
| `SERIAL_TIMEOUT` | `1.0` | Read timeout in seconds. |
| `HOST` | `0.0.0.0` | Network interface to bind HTTP/WebSocket server. |
| `PORT` | `8000` | HTTP port. |
| `RELOAD` | `false` | Enable live auto-reloading when source files or templates change. |


Example `.env` file for physical Raspberry Pi deployment:
```env
MOCK_SERIAL=false
SERIAL_PORT=/dev/ttyUSB0
SERIAL_BAUDRATE=9600
HOST=0.0.0.0
PORT=8000
```

### 4. Running the Application
Using the installed console command:
```bash
yamaha-serial
```
Or directly via Python module:
```bash
python3 -m yamaha_serial.main
```

Once running:
- **Web UI**: Navigate to `http://localhost:8000` (or `http://<pi-ip-address>:8000`).
- **Interactive Swagger Docs**: Navigate to `http://localhost:8000/docs`.

---

## REST API Reference

| Method | Endpoint | Description | Request Body Example |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/state` | Returns the current receiver state | _None_ |
| `POST` | `/api/power` | Set power state (`ON`, `STANDBY`, `TOGGLE`) | `{"power": "ON"}` |
| `POST` | `/api/volume/percent` | Set master volume percentage (0–100%) | `{"percent": 65}` |
| `POST` | `/api/volume/up` | Increase master volume by 1 step (+2%) | _None_ |
| `POST` | `/api/volume/down` | Decrease master volume by 1 step (-2%) | _None_ |
| `POST` | `/api/mute` | Set mute status (`true` / `false`) | `{"mute": true}` |
| `POST` | `/api/mute/toggle` | Toggle mute state | _None_ |
| `POST` | `/api/input` | Switch audio/video source | `{"source": "CD"}` |
| `POST` | `/api/dsp` | Select Cinema DSP sound field program | `{"dsp": "70mm Spectacular"}` |
| `POST` | `/api/raw` | Send raw command string | `{"code": "07EA2"}` |
| `WS` | `/api/ws` | Real-time WebSocket connection for state updates | _JSON state stream_ |

### Supported Input Sources
`PHONO`, `CD`, `TUNER`, `MD/TAPE`, `CD-R`, `DVD`, `D-TV`, `CBL/SAT`, `VCR 1`, `VCR 2`, `VCR 3/DVR`, `V-AUX`

### Supported DSP Programs
`2ch Stereo`, `Direct`, `Surround Standard`, `70mm Spectacular`, `70mm Sci-Fi`, `70mm Adventure`, `70mm General`, `Enhanced`, `Concert Hall 1`, `Concert Hall 2`, `Church`, `Jazz Club`, `Rock Concert`, `Entertainment`, `Music Video`

---

## Raspberry Pi Deployment

### 1. Serial Port Permissions
Ensure your user belongs to the `dialout` group to access serial ports:
```bash
sudo usermod -a -G dialout $USER
```
*(Log out and log back in for changes to take effect.)*

### 2. Auto-start with systemd
A systemd service unit template is included: [yamaha-serial.service](file:///home/jeffl/development/yamaha-serial/yamaha-serial.service).

1. Edit the service file to configure your `User`, `WorkingDirectory`, and `.venv` path:
   ```bash
   nano yamaha-serial.service
   ```
2. Copy to systemd directory and enable:
   ```bash
   sudo cp yamaha-serial.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now yamaha-serial
   ```
3. Check service status and logs:
   ```bash
   sudo systemctl status yamaha-serial
   sudo journalctl -u yamaha-serial -f
   ```

### 3. Persistent USB Serial Device (Optional udev Rule)
To ensure the USB serial adapter always maps to the same device symlink (e.g. `/dev/yamaha-rxz1`):
1. Find vendor and product IDs:
   ```bash
   lsusb
   ```
2. Create `/etc/udev/rules.d/99-yamaha-serial.rules`:
   ```udev
   SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="yamaha-rxz1", MODE="0666"
   ```
3. Reload udev rules:
   ```bash
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```
4. Set `SERIAL_PORT=/dev/yamaha-rxz1` in your `.env`.

---

## Running Tests

Run the unit and integration tests with pytest:
```bash
pytest
```

---

## License

MIT License. See [LICENSE](file:///home/jeffl/development/yamaha-serial/LICENSE) for details.
