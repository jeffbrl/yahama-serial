import sys
import os
from pathlib import Path

# Add bundle directory or current directory to sys.path
base_path = getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)
sys.path.insert(0, str(base_path))
sys.path.insert(0, str(Path(base_path) / "src"))

from yamaha_serial.main import run

if __name__ == "__main__":
    run()
