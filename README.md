# BHQ Sheet Sync — React + FastAPI + PostgreSQL

Source chạy local, không Docker. Hệ thống kết nối Google Sheet bằng OAuth 2.0, đồng bộ listing đa marketplace lúc 08:30 (GMT+7) mỗi ngày, phân loại INSERT / UPDATE / SKIP, lưu dữ liệu chủ chốt ở bảng current và payload đầy đủ ở bảng JSONB detail. Marketplace lấy từ cột `marketplace` trong Sheet.

## Kiến trúc

- `ebay_listings`: dữ liệu chủ chốt để filter/sort/pagination nhanh.
- `ebay_listing_details`: JSONB đầy đủ, chỉ tải khi mở trang chi tiết.
- `ebay_listing_changes`: chỉ ghi các field thay đổi.
- `sync_runs`: thống kê từng lần đồng bộ.
- `google_connections`: refresh token OAuth được mã hóa.

## 1. Cài PostgreSQL

Tạo database:

```sql
CREATE DATABASE ebay_sync;
```

## 2. Google Cloud OAuth

1. Tạo project trên Google Cloud Console.
2. Enable Google Sheets API.
3. Cấu hình OAuth consent screen.
4. Tạo OAuth Client ID loại Web application.
5. Authorized redirect URI:

```text
http://localhost:8000/api/google/callback
```

6. Điền client ID và client secret vào `backend/.env`.

## 3. Chạy backend trên Windows PowerShell

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python generate_fernet_key.py
```

Dán key sinh ra vào `TOKEN_ENCRYPTION_KEY` trong `.env`, sau đó cấu hình `DATABASE_URL`, Google OAuth.

Tạo bảng:

```powershell
python create_tables.py
```

Chạy API:

```powershell
uvicorn app.main:app --reload --port 8000
```

Swagger: `http://localhost:8000/docs`

## 4. Chạy frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Mở `http://localhost:5173`.

## 5. Kết nối Google

Vào **Cấu hình** → **Kết nối Google** → cấp quyền Sheets. Sau khi kết nối, có thể bấm **Đồng bộ ngay** hoặc chờ job 08:30.

## Luồng đồng bộ

1. PostgreSQL advisory lock chống chạy trùng.
2. Đọc snapshot `A1:AQ`.
3. Validate header và `listing_id`.
4. Normalize kiểu dữ liệu và tạo hash.
5. Chưa có business key → INSERT.
6. Có key, hash thay đổi → UPDATE + history.
7. Có key, hash giống → SKIP.
8. Commit database.
9. Đối soát `valid = insert + update + skip`.
10. Clear đúng range snapshot `A2:AQ{last_row}`.

## Chấm tròn trên FE

- Xanh lá: INSERT.
- Xanh dương: UPDATE.
- Xám: SKIP.

`last_sync_action` và `last_sync_run_id` được lưu trên mỗi listing để FE hiển thị kết quả lần đồng bộ gần nhất.

## Lưu ý production

Bản source sử dụng loop query để dễ đọc và chạy ổn ở 10.000 dòng/ngày. Khi dữ liệu tăng mạnh, thay phần import bằng PostgreSQL `COPY` vào staging table rồi `INSERT ... ON CONFLICT ... WHERE data_hash IS DISTINCT` để tối ưu thêm. Không chạy nhiều Uvicorn workers khi APScheduler nằm trong API process; production nên tách scheduler thành process riêng hoặc dùng Celery Beat.
