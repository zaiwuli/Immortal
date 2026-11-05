from pathlib import Path
import os

def get_current_version():
    return os.getenv('SEHUATANG_COLLECTOR_VERSION', '0.1.0')
