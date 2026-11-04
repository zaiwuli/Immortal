import sys

from loguru import logger as uru_logger
import os

from app.core.config import data_path

log_dir = os.path.join(data_path, 'logs')

# 閰嶇疆鏃ュ織锛氭寜澶╁綊妗ｅ埌鎸囧畾鐩綍
def setup_loguru_logger():
    os.makedirs(log_dir, exist_ok=True)

    uru_logger.remove()

    uru_logger.add(
        f"{log_dir}/app.log",
        rotation="00:00",  # 姣忓ぉ鍗堝鍒囧壊
        retention=7,  # 淇濈暀7澶?
        compression="zip",  # 鍘嬬缉澶囦唤
        encoding="utf-8",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    # 娣诲姞鎺у埗鍙拌緭鍑?
    uru_logger.add(
        sink=sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    return uru_logger


logger = setup_loguru_logger()
