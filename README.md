# Fire Tank Online

Fire Tank Online là một trò chơi đấu tăng trực tuyến được xây dựng bằng Python sử dụng giao thức TCP và UDP. Người chơi có thể tham gia vào các trận chiến tăng theo thời gian thực với các tính năng như bắn, nạp đạn và quản lý máu.

## Tính Năng

- Trận chiến tăng nhiều người chơi theo thời gian thực
- Hỗ trợ 2 người chơi cùng lúc
- Cơ chế di chuyển và bắn mượt mà
- Hệ thống quản lý máu và đạn
- Đồng bộ hóa trạng thái trò chơi qua giao thức TCP/UDP
- Giao diện tương tác với các chỉ số trạng thái trò chơi
- Hệ thống sẵn sàng cho người chơi
- Chức năng khởi động lại trò chơi

## Yêu Cầu Hệ Thống

- Python 3.8 trở lên
- Thư viện Pygame (có sẵn trong Python chuẩn)
- Kết nối mạng cho chế độ nhiều người chơi

## Cài Đặt

1. Clone repository:
```bash
git clone https://github.com/hiennam2803/Fire_tank_Online.git
cd Fire_tank_Online
```

2. Cài dependencies (khuyến nghị dùng virtual environment nhưng không bắt buộc)

2a Cách an toàn (khuyến nghị): tạo virtualenv và cài tất cả:
```powershell
python -m venv .venv
# nếu PowerShell chặn script, cho phép tạm thời trong session hiện tại:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

2b Nếu bạn KHÔNG muốn dùng virtualenv (cài trực tiếp vào Python hệ thống):
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Lưu ý: `requirements.txt` hiện gồm cả `pygame_gui` như một tùy chọn UI; nếu bạn không muốn cài các package phụ, chỉ cài `pygame` và `pymysql` bằng:
```powershell
python -m pip install pygame pymysql
# hoặc cài pygame_gui riêng nếu cần giao diện nâng cao
python -m pip install pygame_gui
```

3. Nếu bạn cài thêm package mới (ví dụ `pygame_gui`) nên cập nhật `requirements.txt` và commit để mọi người cùng cài theo.

## Cách Chơi

### Khởi Động Server

1. Mở terminal và chạy:
```bash
python main.py server
```

### Tham Gia Với Tư Cách Người Chơi

1. Mở terminal mới và chạy:
```bash
python main.py client
```

2. Khi được yêu cầu, nhập địa chỉ IP của server:
   - Sử dụng `localhost` hoặc nhấn Enter để test cục bộ
   - Nhập địa chỉ IP của server để chơi qua mạng

### Điều Khiển

- **Phím mũi tên**: Di chuyển tăng và ngắm
- **Space**: Bắn
- **R**: Nạp đạn (thời gian chờ 7 giây)
- **Space**: Sẵn sàng (trong màn hình chờ)
- **T**: Yêu cầu khởi động lại (sau khi game kết thúc)

### Luật Chơi

- Mỗi người chơi bắt đầu với 100 HP và 10 viên đạn
- Bắn trúng gây 25 sát thương
- Có thể nạp lại đạn (mất 7 giây)
- Trò chơi kết thúc khi HP của một người chơi về 0
- Cả hai người chơi phải sẵn sàng để bắt đầu trò chơi mới

## Cấu Trúc Dự Án

```
Fire_tank_Online/
├── client/
│   ├── client.py     # Logic phía người chơi
│   └── gui.py        # Giao diện và hiển thị trò chơi
├── common/
│   └── messages.py   # Constants và kiểu tin nhắn dùng chung
├── server/
│   ├── game.py       # Game engine và logic
│   └── server.py     # Triển khai server
├── tests/
│   └── test_game.py  # Unit tests
└── main.py           # Điểm khởi đầu
```

## Chi Tiết Kỹ Thuật

### Mạng

- **Cổng TCP**: 5555 (Dùng cho cập nhật trạng thái game đáng tin cậy)
- **Cổng UDP**: 5556 (Dùng cho cập nhật vị trí thời gian thực)
- Hỗ trợ chơi qua LAN và internet

### Thông Số Game

- Kích thước màn hình: 800x600 pixels
- Thời gian hồi bắn: 0.5 giây
- Thời gian nạp đạn: 7.0 giây
- Số đạn tối đa: 10 viên
- Máu người chơi: 100 điểm
- Sát thương đạn: 25 điểm

## Phát Triển

### Chạy Tests

```bash
python -m unittest tests/test_game.py
```

### Hướng Phát Triển
Dự án có thể mở rộng với các tính năng bổ sung như:
- Power-up và kỹ năng đặc biệt
- Các loại tăng khác nhau
- Hỗ trợ nhiều người chơi hơn
- Theo dõi điểm số
- Các chế độ chơi khác nhau

## Giấy Phép

Dự án này là mã nguồn mở và có sẵn dưới Giấy phép MIT.

## Người Đóng Góp

- hiennam2803 (Chủ Dự Án)

## Xử Lý Sự Cố

1. **Vấn Đề Kết Nối**
   - Đảm bảo server đang chạy trước khi khởi động client
   - Kiểm tra cài đặt tường lửa khi chơi qua mạng
   - Xác nhận địa chỉ IP chính xác

2. **Vấn Đề Hiển Thị**
   - Đảm bảo Python và Pygame được cài đặt đúng cách
   - Kiểm tra yêu cầu độ phân giải tối thiểu (800x600)

## Hướng dẫn commit
# 1 Kiểm tra lần cuối
   git status --short

# 2 Stage chỉ các thay đổi tracked (an toàn: không thêm untracked files)
   git add -u

# 3 Xem file đã staged
   git status --short
   or
   git diff --staged --name-only

# 4 Commit với message (ví dụ)
   git commit -m "Text"

## Hỗ Trợ

Để được hỗ trợ, báo lỗi hoặc đóng góp, vui lòng truy cập [GitHub repository](https://github.com/hiennam2803/Fire_tank_Online)
