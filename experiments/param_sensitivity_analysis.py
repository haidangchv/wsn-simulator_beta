import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


import copy
import yaml
import json
import pandas as pd
from core.network import WirelessSensorNetwork
from simulation.simulator import WSNSimulator
from topology.deployment import deploy_sensors, create_sink

# Load base config
with open("config.yaml", "r", encoding="utf-8") as f:
    base_cfg = yaml.safe_load(f)

# Base simulation configuration for parametric analysis
# E0 = 2.0 J, R = 200 m, 500 sensors, seed = 42, 100 rounds
BASE_CONFIG = copy.deepcopy(base_cfg)
BASE_CONFIG["sensor"]["initial_energy_j"] = 2.0
BASE_CONFIG["sensor"]["transmission_range_m"] = 200
BASE_CONFIG["sensor"]["energy_threshold_ratio"] = 0.20
BASE_CONFIG["packet"]["payload_size_bytes"] = 128
BASE_CONFIG["packet_crypto"]["enabled"] = False
BASE_CONFIG["routing"]["algorithm"] = "lb_ecmhr"
BASE_CONFIG["routing"]["lb_ecmhr"] = {
    "load_window_rounds": 24,
    "overload_factor": 2.0,
    "recovery_factor": 1.2,
    "max_extra_hops": 1,
    "allow_overload_fallback": True,
    "route_update_interval_rounds": 1
}

def run_simulation_instance(cfg, algorithm="lb_ecmhr", rounds=100):
    sensors = deploy_sensors(cfg)
    sink = create_sink(cfg)
    net = WirelessSensorNetwork(sensors=sensors, sink=sink)
    net.build_topology()
    sim = WSNSimulator(network=net, config=cfg, routing_algorithm=algorithm)
    sim.run(rounds=rounds)
    m = sim.get_metrics()
    return {
        "algorithm": algorithm,
        "rounds": sim.current_round,
        "fnd_round": sim.fnd_round if sim.fnd_round is not None else 100,
        "dead_nodes": m.get("dead_nodes", 0),
        "alive_nodes": m.get("alive_nodes", 0),
        "low_energy_nodes": m.get("low_energy_nodes", 0),
        "total_energy_consumed_j": round(m.get("total_energy_consumed_j", 0.0), 2),
        "average_hop_count": round(m.get("average_hop_count", 0.0), 2),
        "average_delay_ms": round(m.get("average_delay_ms", 0.0), 2),
        "pdr": round(m.get("pdr", 0.0) * 100, 2),
        "delivered_data_mb": round(m.get("delivered_data_mb", 0.0), 2),
        "energy_efficiency": round(m.get("energy_efficiency_bits_per_j", 0.0), 0),
        "relay_load_cv": round(m.get("relay_load_cv", 0.0), 3),
        "overloaded_relay_count": m.get("overloaded_relay_count", 0),
        "detour_route_count": m.get("detour_route_count", 0),
        "connectivity_ratio": round(m.get("routing_connectivity_ratio", 1.0) * 100, 2),
        "connectivity_50_round": m.get("connectivity_50_round", None)
    }

print("[*] BẮT ĐẦU QUY TRÌNH 10 CÔNG VIỆC: ĐO ĐẠC ĐỘ NHẠY THAM SỐ LB-ECMHR...")
results = {}

# -------------------------------------------------------------
# 1. Thí nghiệm 1: Xác định ngưỡng năng lượng alpha (0.10 -> 0.30)
# -------------------------------------------------------------
print("\n[1/6] Chạy Thí nghiệm 1: Quét ngưỡng năng lượng alpha in [0.10, 0.15, 0.20, 0.25, 0.30]...")
alpha_results = []
for alpha in [0.10, 0.15, 0.20, 0.25, 0.30]:
    cfg = copy.deepcopy(BASE_CONFIG)
    cfg["sensor"]["energy_threshold_ratio"] = alpha
    cfg["routing"]["energy_threshold_ratio"] = alpha
    res = run_simulation_instance(cfg, "lb_ecmhr", 100)
    res["alpha"] = alpha
    res["threshold_j"] = round(alpha * 2.0, 2)
    alpha_results.append(res)
    print(f"   - alpha={alpha:.2f} ({res['threshold_j']}J): FND={res['fnd_round']}, Dead={res['dead_nodes']}, Energy={res['total_energy_consumed_j']}J, PDR={res['pdr']}%")
results["exp1_alpha"] = alpha_results

# -------------------------------------------------------------
# 2. Thí nghiệm 2: Xác định cửa sổ tải W in [6, 12, 24, 48]
# -------------------------------------------------------------
print("\n[2/6] Chạy Thí nghiệm 2: Quét cửa sổ tải W in [6, 12, 24, 48]...")
w_results = []
for w in [6, 12, 24, 48]:
    cfg = copy.deepcopy(BASE_CONFIG)
    cfg["routing"]["lb_ecmhr"]["load_window_rounds"] = w
    res = run_simulation_instance(cfg, "lb_ecmhr", 100)
    res["load_window_w"] = w
    w_results.append(res)
    print(f"   - W={w:2d}h: Relay_CV={res['relay_load_cv']}, Overloaded={res['overloaded_relay_count']}, Detours={res['detour_route_count']}, PDR={res['pdr']}%")
results["exp2_window"] = w_results

# -------------------------------------------------------------
# 3. Thí nghiệm 3: Xác định ngưỡng quá tải beta in [1.5, 2.0, 2.5, 3.0]
# -------------------------------------------------------------
print("\n[3/6] Chạy Thí nghiệm 3: Quét ngưỡng quá tải beta in [1.5, 2.0, 2.5, 3.0]...")
beta_results = []
for beta in [1.5, 2.0, 2.5, 3.0]:
    cfg = copy.deepcopy(BASE_CONFIG)
    cfg["routing"]["lb_ecmhr"]["overload_factor"] = beta
    # Đảm bảo recovery_factor < beta
    cfg["routing"]["lb_ecmhr"]["recovery_factor"] = min(1.2, beta - 0.3)
    res = run_simulation_instance(cfg, "lb_ecmhr", 100)
    res["beta"] = beta
    beta_results.append(res)
    print(f"   - beta={beta:.1f}: Relay_CV={res['relay_load_cv']}, AvgHop={res['average_hop_count']}, Overloaded={res['overloaded_relay_count']}, Energy={res['total_energy_consumed_j']}J")
results["exp3_beta"] = beta_results

# -------------------------------------------------------------
# 4. Thí nghiệm 4: Xác định ngưỡng phục hồi gamma in [0.8, 1.0, 1.2, 1.5]
# -------------------------------------------------------------
print("\n[4/6] Chạy Thí nghiệm 4: Quét ngưỡng phục hồi gamma in [0.8, 1.0, 1.2, 1.5] (beta=2.0)...")
gamma_results = []
for gamma in [0.8, 1.0, 1.2, 1.5]:
    cfg = copy.deepcopy(BASE_CONFIG)
    cfg["routing"]["lb_ecmhr"]["recovery_factor"] = gamma
    res = run_simulation_instance(cfg, "lb_ecmhr", 100)
    res["gamma"] = gamma
    gamma_results.append(res)
    print(f"   - gamma={gamma:.1f}: Relay_CV={res['relay_load_cv']}, Detours={res['detour_route_count']}, Energy={res['total_energy_consumed_j']}J")
results["exp4_gamma"] = gamma_results

# -------------------------------------------------------------
# 5. Thí nghiệm 5: Xác định số hop đi vòng Delta_H in [0, 1, 2]
# -------------------------------------------------------------
print("\n[5/6] Chạy Thí nghiệm 5: Quét số hop đi vòng Delta_H in [0, 1, 2]...")
delta_h_results = []
for delta_h in [0, 1, 2]:
    cfg = copy.deepcopy(BASE_CONFIG)
    cfg["routing"]["lb_ecmhr"]["max_extra_hops"] = delta_h
    res = run_simulation_instance(cfg, "lb_ecmhr", 100)
    res["delta_h"] = delta_h
    delta_h_results.append(res)
    print(f"   - Delta_H={delta_h}: AvgHop={res['average_hop_count']}, Delay={res['average_delay_ms']}ms, Energy={res['total_energy_consumed_j']}J, Detours={res['detour_route_count']}")
results["exp5_delta_h"] = delta_h_results

# -------------------------------------------------------------
# 6. Ablation Study: Bóc tách từng thành phần của thuật toán
# -------------------------------------------------------------
print("\n[6/6] Chạy Ablation Study (Loại bỏ từng thành phần)...")
ablation_results = []

# Cấu hình A: Minimum-Hop thuần túy
cfg_a = copy.deepcopy(BASE_CONFIG)
res_a = run_simulation_instance(cfg_a, "minimum_hop", 100)
res_a["name"] = "1. Minimum-Hop (Baseline)"
res_a["desc"] = "Chỉ tìm đường ngắn nhất, không ràng buộc năng lượng, không cân bằng tải"
ablation_results.append(res_a)
print(f"   - Baseline Min-Hop: FND={res_a['fnd_round']}, Dead={res_a['dead_nodes']}, Energy={res_a['total_energy_consumed_j']}J")

# Cấu hình B: Energy-Constrained (chỉ có alpha, không cân bằng tải)
cfg_b = copy.deepcopy(BASE_CONFIG)
cfg_b["routing"]["lb_ecmhr"]["overload_factor"] = 999.0  # Vô hiệu hóa cân bằng tải
res_b = run_simulation_instance(cfg_b, "lb_ecmhr", 100)
res_b["name"] = "2. Energy-Constrained (EC-only)"
res_b["desc"] = "Có ngưỡng alpha=0.2 nhưng không né tránh quá tải (không Load Balancing)"
ablation_results.append(res_b)
print(f"   - EC-only: FND={res_b['fnd_round']}, Dead={res_b['dead_nodes']}, Energy={res_b['total_energy_consumed_j']}J")

# Cấu hình C: LB-ECMHR không cho đi vòng (Delta_H = 0)
cfg_c = copy.deepcopy(BASE_CONFIG)
cfg_c["routing"]["lb_ecmhr"]["max_extra_hops"] = 0
res_c = run_simulation_instance(cfg_c, "lb_ecmhr", 100)
res_c["name"] = "3. LB-ECMHR (Delta_H = 0)"
res_c["desc"] = "Có nhận diện quá tải nhưng không cho phép đi vòng (bắt buộc cùng số hop)"
ablation_results.append(res_c)
print(f"   - Delta_H=0: FND={res_c['fnd_round']}, Dead={res_c['dead_nodes']}, Energy={res_c['total_energy_consumed_j']}J")

# Cấu hình D: LB-ECMHR không Hysteresis (gamma xấp xỉ beta = 1.99 so với 2.0)
cfg_d = copy.deepcopy(BASE_CONFIG)
cfg_d["routing"]["lb_ecmhr"]["recovery_factor"] = 1.99
res_d = run_simulation_instance(cfg_d, "lb_ecmhr", 100)
res_d["name"] = "4. LB-ECMHR (No Hysteresis: gamma ≈ beta)"
res_d["desc"] = "Ngưỡng phục hồi sát ngưỡng quá tải (gamma = 1.99 so với beta = 2.0), không có vùng đệm trễ"
ablation_results.append(res_d)
print(f"   - No Hysteresis: FND={res_d['fnd_round']}, Dead={res_d['dead_nodes']}, Energy={res_d['total_energy_consumed_j']}J")


# Cấu hình E: LB-ECMHR Đầy đủ (Full Configuration)
cfg_e = copy.deepcopy(BASE_CONFIG)
res_e = run_simulation_instance(cfg_e, "lb_ecmhr", 100)
res_e["name"] = "5. LB-ECMHR (Full Model)"
res_e["desc"] = "Cấu hình chuẩn đầy đủ: alpha=0.2, W=24, beta=2.0, gamma=1.2, Delta_H=1"
ablation_results.append(res_e)
print(f"   - Full LB-ECMHR: FND={res_e['fnd_round']}, Dead={res_e['dead_nodes']}, Energy={res_e['total_energy_consumed_j']}J")

results["ablation_study"] = ablation_results

# Lưu kết quả vào JSON để đưa vào tài liệu
output_path = Path("experiments/sensitivity_results.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n[OK] Đã hoàn thành toàn bộ thí nghiệm! Kết quả lưu tại: {output_path}")
