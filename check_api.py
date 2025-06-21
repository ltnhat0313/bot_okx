# File: check_api.py
# Mục đích: Kiểm tra nhanh xem thông tin API trong file .env có hợp lệ không.

import os
from dotenv import load_dotenv
from modules.api_integration import OKXIntegration
import logging

# Tắt bớt log không cần thiết để output gọn gàng
logging.basicConfig(level=logging.CRITICAL) 

def check_credentials():
    """
    Hàm chính để kiểm tra thông tin xác thực API.
    """
    print("Đang tải thông tin từ file .env...")
    load_dotenv()

    api_key = os.getenv('OKX_API_KEY')
    secret_key = os.getenv('OKX_SECRET_KEY')
    passphrase = os.getenv('OKX_PASSPHRASE')

    if not all([api_key, secret_key, passphrase]):
        print("❌ LỖI: Không tìm thấy đủ thông tin API Key, Secret Key, Passphrase trong file .env.")
        return

    print("Đã tải xong. Đang thử kết nối đến OKX với thông tin đã cung cấp...")

    # Tạo một instance của OKXIntegration ở chế độ TEST
    api = OKXIntegration(api_key, secret_key, passphrase, is_test=True)

    # Thử gọi một hàm cần xác thực (private endpoint)
    balance = api.get_account_balance('USDT')

    print("-" * 40)
    # Kiểm tra kết quả
    if balance is not None:
        print(f"✅ XÁC THỰC THÀNH CÔNG!")
        print(f"   Số dư USDT của bạn trên tài khoản Demo là: {balance:,.2f}")
        print("   Bạn có thể tự tin sử dụng thông tin này để chạy bot chính.")
    else:
        print(f"❌ XÁC THỰC THẤT BẠI!")
        print("   Lý do: Passphrase, API Key hoặc Secret Key không chính xác.")
        print("   Hành động: Vui lòng kiểm tra lại file .env hoặc thực hiện theo hướng dẫn tạo lại bộ API Key mới một cách cẩn thận.")
    print("-" * 40)

if __name__ == "__main__":
    check_credentials()