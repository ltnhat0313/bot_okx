# File: logging_config.py

import logging
import os

def setup_logging(log_file='logs/trading_bot.log'):
    """
    Cấu hình logging để ghi ra file và hiển thị trên console.
    Linh hoạt hơn bằng cách cho phép chỉ định file log.
    """
    # Tạo thư mục logs nếu nó chưa tồn tại
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Lấy logger gốc
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Xóa các handler cũ nếu đã tồn tại để tránh log bị lặp
    if logger.hasHandlers():
        logger.handlers.clear()

    # Định dạng cho log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Handler để ghi log ra file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler để hiển thị log trên console (màn hình terminal)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger