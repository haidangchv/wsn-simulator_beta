#!/usr/bin/env python3
"""
Benchmark script for Lightweight Packet Encryption (AES-128-CCM-8).
Measures encryption and decryption latency on 10,000 packets.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import time

import statistics
from data.packet_crypto import PacketCrypto



def run_benchmark(num_packets: int = 10000):
    print(f"[*] Khởi tạo PacketCrypto (AES-128-CCM, tag_length=8)...")
    crypto = PacketCrypto()

    # Pre-generate sample data
    source_ids = [i % 500 for i in range(num_packets)]
    seq_numbers = [i + 1 for i in range(num_packets)]
    values = [25.0 + (i % 100) * 0.15 for i in range(num_packets)]

    print(f"[*] Bắt đầu benchmark {num_packets:,} phép mã hóa...")
    ciphertexts = []
    enc_times = []

    for sid, seq, val in zip(source_ids, seq_numbers, values):
        t0 = time.perf_counter()
        ct = crypto.encrypt_float32(source_id=sid, sequence_number=seq, value=val)
        t1 = time.perf_counter()
        ciphertexts.append(ct)
        enc_times.append((t1 - t0) * 1000.0)  # ms

    print(f"[*] Bắt đầu benchmark {num_packets:,} phép giải mã và kiểm tra tag...")
    dec_times = []
    for sid, seq, ct in zip(source_ids, seq_numbers, ciphertexts):
        t0 = time.perf_counter()
        recovered = crypto.decrypt_float32(source_id=sid, sequence_number=seq, ciphertext=ct)
        t1 = time.perf_counter()
        dec_times.append((t1 - t0) * 1000.0)  # ms

    avg_enc = statistics.mean(enc_times)
    median_enc = statistics.median(enc_times)
    avg_dec = statistics.mean(dec_times)
    median_dec = statistics.median(dec_times)

    enc_throughput = num_packets / (sum(enc_times) / 1000.0)
    dec_throughput = num_packets / (sum(dec_times) / 1000.0)

    print("\n" + "=" * 60)
    print("    KẾT QUẢ BENCHMARK MÃ HÓA GÓI TIN (AES-128-CCM-8)")
    print("=" * 60)
    print(f"  Số lượng mẫu thử nghiệm     : {num_packets:,} packets")
    print(f"  Kích thước dữ liệu gốc      : 4 Bytes (float32)")
    print(f"  Kích thước sau mã hóa (tag) : 12 Bytes (+8 Bytes tag)")
    print("-" * 60)
    print(f"  Thời gian mã hóa trung bình : {avg_enc:.5f} ms/packet ({avg_enc * 1000:.2f} µs)")
    print(f"  Thời gian mã hóa trung vị   : {median_enc:.5f} ms/packet")
    print(f"  Tốc độ mã hóa (Throughput)  : {enc_throughput:,.0f} packets/giây")
    print("-" * 60)
    print(f"  Thời gian giải mã trung bình: {avg_dec:.5f} ms/packet ({avg_dec * 1000:.2f} µs)")
    print(f"  Thời gian giải mã trung vị  : {median_dec:.5f} ms/packet")
    print(f"  Tốc độ giải mã (Throughput) : {dec_throughput:,.0f} packets/giây")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_benchmark(10000)
