# AlphaTradeAI - Bot Giao Dịch Tự Động (Phiên bản 2025)

Đây là dự án bot giao dịch tự động cho thị trường tiền điện tử, sử dụng kết hợp phân tích kỹ thuật, phân tích bối cảnh và quản lý rủi ro để thực hiện giao dịch trên sàn OKX.

*Cập nhật lần cuối: Tháng 6, 2025*

## Tính năng

- **Phân tích kỹ thuật (TA Engine):** Sử dụng `pandas-ta` để tính toán RSI, EMA, và ATR.
- **Tích hợp API (API Integration):** Cấu trúc linh hoạt hỗ trợ nhiều sàn (đã triển khai cho OKX).
- **Quản lý rủi ro (Risk Management):** Tự động tính toán kích thước vị thế dựa trên % rủi ro.
- **Hệ thống tính điểm:** Tổng hợp điểm từ nhiều nguồn để ra quyết định khách quan.
- **Logging & Database:** Ghi lại mọi hoạt động vào file log và lưu lịch sử giao dịch vào SQLite.

## Hướng dẫn Cài đặt

1.  **Tạo thư mục dự án và các file** theo cấu trúc đã hiển thị.

2.  **Tạo và kích hoạt môi trường ảo:**
    ```bash
    python -m venv venv
    # macOS/Linux: source venv/bin/activate
    # Windows: .\\venv\\Scripts\\activate
    ```

3.  **Cài đặt thư viện:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Tạo file `.env`** từ file `.env.example` và điền thông tin API Key của bạn (bắt đầu với tài khoản Demo Trading trên OKX để an toàn).

5.  **Khởi tạo cơ sở dữ liệu (chạy một lần):**
    ```bash
    python -c "from modules.database import init_db; init_db()"
    ```

## Cách chạy Bot

```bash
python bot.py