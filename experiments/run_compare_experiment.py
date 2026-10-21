import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import copy
import yaml
from experiments.compare_routing import compare_algorithms


with open("config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

# Cấu hình thử nghiệm theo đề tài:
# Area 2000x2000, 500 sensors, seed 42, Sink (1000, 1000)
# Range = 200m, E0 = 2.0J, threshold = 0.20, packet = 128B
cfg_test = copy.deepcopy(cfg)
cfg_test["sensor"]["initial_energy_j"] = 2.0
cfg_test["sensor"]["transmission_range_m"] = 200
cfg_test["sensor"]["energy_threshold_ratio"] = 0.20
cfg_test["packet"]["payload_size_bytes"] = 128
cfg_test["packet_crypto"]["enabled"] = False

print("Đang chạy thực nghiệm so sánh Minimum-Hop và LB-ECMHR (100 rounds)...")
df, history_data = compare_algorithms(cfg_test, rounds=100, return_history=True)

print("\n" + "=" * 60)
print("       BẢNG KẾT QUẢ SO SÁNH ĐỊNH TUYẾN (100 ROUNDS)")
print("=" * 60)

cols = [
    "average_hop_count", "average_delay_ms", "pdr",
    "throughput_bps", "delivered_data_mb", "fnd_round", "hnd_round", "lnd_round",
    "delivered_bytes_at_fnd", "connectivity_50_round", "relay_load_cv",
    "energy_efficiency_bits_per_j", "total_energy_consumed_j", "dead_nodes"
]

for idx, row in df.iterrows():
    algo = row.get("algorithm", "N/A")
    print(f"\n[+] Thuật toán: {algo.upper()}")
    for c in cols:
        val = row.get(c, "N/A")
        print(f"    - {c:30s}: {val}")

print("\n" + "=" * 60)
