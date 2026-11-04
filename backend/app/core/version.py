from pathlib import Path
import os

def get_current_version():
    return os.getenv('IMMORTAL_VERSION', '0.1.0')
