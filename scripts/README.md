# Kiểm tra và tái tạo bài nộp

Từ thư mục gốc:

```bash
python3 -m pytest -q tests
python3 run_all.py all
python3 scripts/check_submission.py
```

Pipeline dùng MSSV ở dòng đầu `REPORT.md`, ngân sách mặc định và `hazard.json` đã khóa. Không dùng `--quick` cho evidence nộp. Nếu chạy lại pipeline, đối chiếu báo cáo với JSON mới; thời gian chạy và timestamp có thể thay đổi.

Ảnh được chụp trực tiếp từ viewer bằng Chrome headless, giữ nguyên mã viewer. Script mở file lab, chọn kịch bản, dừng ở frame sự kiện và chụp toàn trang; `manifest.json` ghi nguồn, thời điểm và sự kiện. Ảnh hazard chụp lúc phanh đang bắt đầu vì cảnh này không có va chạm.

Tái tạo ảnh trên macOS đã cài Chrome:

```bash
npm install --prefix /tmp/lab11-browser playwright
PLAYWRIGHT_MODULE=/tmp/lab11-browser/node_modules/playwright \
CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
node scripts/capture_shots.cjs
```

Playwright chỉ phục vụ chụp ảnh; phần lab vẫn chỉ cần NumPy và pytest, cùng Node cho parity test. Trên máy khác, đặt `CHROME_PATH` tới Chrome/Chromium đã cài hoặc dùng Chromium của Playwright.

Trong ảnh sửa planner, script chạy policy chọn trên đúng tham số của một run đã lưu. Policy gốc là bóng mờ. Một bản sao dữ liệu được nạp trong bộ nhớ trình duyệt, không thay đổi `evidence/viewer.json`.
