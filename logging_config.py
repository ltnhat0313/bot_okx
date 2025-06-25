import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from config import LOG_LEVEL, LOG_FILE_PATH, LOG_MAX_BYTES, LOG_BACKUP_COUNT

def configure_logging():
    """
    Cấu hình hệ thống logging tập trung cho toàn bộ ứng dụng.
    """
    root_logger = logging.getLogger()
    log_level_const = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level_const)
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.encoding = 'utf-8'
    
    try:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH, 
            maxBytes=LOG_MAX_BYTES, 
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8' 
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Lỗi nghiêm trọng khi thiết lập file handler cho logging: {e}")

    root_logger.addHandler(console_handler)
    logging.info("Hệ thống Logging đã được cấu hình thành công.")
