# 🔐 Lightweight Packet Encryption (AES-128-CCM-8)

Tài liệu kỹ thuật về cơ chế mã hóa và giải mã gói tin nhẹ (Lightweight Packet Encryption) được tích hợp trong WSN Simulator.

---

## 1. Tổng quan & Mục tiêu thiết kế

Trong mạng cảm biến không dây (WSN), bảo vệ dữ liệu môi trường nhạy cảm chống nghe lén và sửa đổi giả mạo là rất quan trọng, nhưng năng lượng và tài nguyên tính toán của các nút cảm biến lại vô cùng hạn chế.

Cơ chế này sử dụng chuẩn **AES-128-CCM** với **authentication tag 8 byte** (chuẩn NIST SP 800-38C / RFC 3610) theo mô hình **End-to-End Encryption**:

```
[Sensor Node] 
  │  Mã hóa giá trị đo (float32 / payload)
  │  Sinh 8-byte authentication tag
  ▼
[Gói tin: Header 12 B + Payload + Tag 8 B]
  │
  ├──► [Relay Node A] ──► Chuyển tiếp thuần túy (Forwarding), không giải mã/mã hóa lại
  │
  ├──► [Relay Node B] ──► Chuyển tiếp thuần túy (Forwarding), không giải mã/mã hóa lại
  │
  ▼
[Sink Node]
  │  Kiểm tra tính toàn vẹn (8-byte tag) & Giải mã
  │  Chỉ nạp dữ liệu hợp lệ vào Environmental Collector (Heatmap / ELQI)
  ▼
[Dữ liệu sạch & Đáng tin cậy]
```

### Điểm tối ưu trọng tâm
- **Chỉ mã hóa 1 lần tại nguồn và giải mã 1 lần tại Sink**: Các relay trung gian trong thuật toán LB-ECMHR không cần can thiệp giải mã, do đó không phát sinh chi phí tính toán mật mã tại từng hop.
- **Không thay đổi thuật toán định tuyến**: Cấu trúc định tuyến LB-ECMHR, tiêu chí cân bằng tải và tính toán chất lượng sống ELQI hoàn toàn độc lập.
- **Tính toán năng lượng chính xác**: Chi phí năng lượng được đo đạc tự nhiên thông qua kích thước gói tin tăng thêm (+8 byte tag) tác động lên mô hình vô tuyến tuyến tính $E_{TX}$ và $E_{RX}$.

---

## 2. Cấu trúc Nonce & Cơ chế Zero-Overhead

AES-CCM yêu cầu một **Nonce 13 bytes** duy nhất cho mỗi phép mã hóa để đảm bảo an toàn tuyệt đối chống tấn công lặp lại (replay attacks).

Thay vì phải phát thêm 13 bytes Nonce trên đường truyền không dây, Nonce được kiến tạo tất định (deterministic) từ các trường đã có sẵn trong Header của Packet:

| Byte Offset | Độ dài | Trường dữ liệu | Mô tả |
| :--- | :--- | :--- | :--- |
| **0 – 3** | 4 Bytes | `source_id` | Định danh cảm biến nguồn (Big-Endian uint32) |
| **4 – 11** | 8 Bytes | `sequence_number` | Số thứ tự gói tin của node (Big-Endian uint64) |
| **12** | 1 Byte | `flag` | Byte cờ hướng truyền (`0x00`) |

> **Lợi ích:** Sink chỉ cần trích xuất `source_id` và `sequence_number` từ header của gói tin là có thể khôi phục chính xác Nonce để giải mã. **Overhead truyền Nonce qua mạng vô tuyến = 0 Byte**.

---

## 3. Chi phí Kích thước gói tin & Năng lượng

AES-CCM không làm giãn kích thước phần ciphertext so với plaintext, chỉ bổ sung đúng **8 bytes authentication tag**.

| Dữ liệu gốc | Packet trước mã hóa (Header 12 B) | Sau mã hóa (+8 B Tag) | Mức tăng |
| :--- | :--- | :--- | :--- |
| **4 B (float32)** | 16 B | 24 B | +50.0% |
| **32 B** | 44 B | 52 B | +18.2% |
| **64 B (Mặc định)** | 76 B | 84 B | +10.5% |
| **128 B** | 140 B | 148 B | +5.7% |

### Mô hình Năng lượng vô tuyến
Năng lượng tiêu hao được tính toán dựa trên `packet.payload_size_bytes` đã bao gồm 8 bytes tag:
- **Năng lượng phát:** $E_{TX}(k, d) = k \cdot E_{elec} + k \cdot \epsilon \cdot d^{\alpha}$
- **Năng lượng nhận:** $E_{RX}(k) = k \cdot E_{elec}$

Với $k = (L_{raw} + 8) \times 8$ bits. Việc tăng 8 bytes tag làm tăng nhẹ năng lượng TX/RX trên mỗi hop mà không làm sai lệch mô hình phần cứng vô tuyến.

---

## 4. Kết quả Thực nghiệm & Benchmark

Thực hiện benchmark trên 10.000 phép mã hóa và giải mã độc lập (`scripts/benchmark_packet_crypto.py`):

| Thao tác | Thời gian trung bình | Tốc độ xử lý (Throughput) |
| :--- | :--- | :--- |
| **Mã hóa (Sensor)** | ~0.00167 ms/packet (1.67 µs) | ~598,000 packets/giây |
| **Giải mã & Xác thực (Sink)** | ~0.00159 ms/packet (1.59 µs) | ~628,000 packets/giây |

> **Nhận xét:** Độ trễ CPU trên môi trường mô phỏng chỉ khoảng ~1.6 µs/packet, hoàn toàn không gây nút thắt cổ chai cho tốc độ mô phỏng WSN.

---

## 5. Hướng dẫn Tích hợp & Sử dụng

### 5.1. Cài đặt thư viện phụ thuộc
```bash
pip install cryptography
```

### 5.2. Cấu hình trong `config.yaml`
```yaml
packet_crypto:
  enabled: true              # Bật/tắt cơ chế bảo mật
  algorithm: "aes_ccm_128"
  tag_bytes: 8               # Kích thước authentication tag
  header_bytes: 12
  cpu_energy_nj_per_byte: 1.2 # Năng lượng tiêu thụ CPU của vi điều khiển sensor
```

### 5.3. Sử dụng API độc lập
```python
from data.packet_crypto import PacketCrypto, CryptoAuthenticationError

crypto = PacketCrypto()

# Mã hóa tại Sensor
ciphertext = crypto.encrypt_float32(
    source_id=15,
    sequence_number=1,
    value=31.73
)

# Giải mã tại Sink
try:
    decrypted = crypto.decrypt_float32(
        source_id=15,
        sequence_number=1,
        ciphertext=ciphertext
    )
    print(f"Giá trị khôi phục: {decrypted:.2f}")
except CryptoAuthenticationError:
    print("Cảnh báo: Dữ liệu bị giả mạo hoặc sai khóa/nonce!")
```

### 5.4. Chạy Benchmark
```bash
python scripts/benchmark_packet_crypto.py
```

### 5.5. Chạy bộ kiểm thử tự động
```bash
pytest tests/test_packet_crypto.py -v
```

---

## 6. Tính tương thích với Checkpoint (Determinism)

Cơ chế checkpoint của hệ thống sử dụng định dạng nén `.wsnchk.gz` qua `pickle`. 
Đối tượng `PacketCrypto` được thiết kế tương thích đặc biệt (`__getstate__` / `__setstate__`) để:
1. **Lưu trữ an toàn khóa bí mật** dưới dạng `bytes` nguyên bản, tránh lỗi con trỏ C-extension của OpenSSL khi serialize.
2. **Khôi phục nguyên vẹn** trạng thái mã hóa, bộ đếm sequence numbers và đối tượng cipher.
3. Khi tiếp tục chạy từ checkpoint, Sink vẫn giải mã chính xác 100% các gói tin của các round kế tiếp mà không xảy ra xung đột nonce.
