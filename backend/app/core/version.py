from pathlib import Path
import os

def get_current_version():
    return os.getenv('SHILIU_VERSION', '0.1.0')
