"""
Script: run_lnd_experiments.py
Mô tả: Thực hiện mô phỏng toàn bộ vòng đời mạng (Full Network Lifecycle until LND - Last Node Death)
cho 4 mô hình định tuyến:
  1. Minimum-Hop (Baseline)
  2. EC-only (True Energy-Constrained Minimum-Hop, alpha=0.20, không cân bằng tải)
  3. LB-ECMHR (Hard Threshold alpha=0.20)
  4. LB-ECMHR (Soft Reserve Fallback alpha=0.20 -> 0.02)
Trong Kịch bản B (Extended Lifecycle), mỗi nút cảm biến còn sống tiêu thụ một mức năng lượng nền
cơ sở (Basal Sensing, MCU & Beacon Maintenance Energy: E_basal = 0.002 J/round) bên cạnh năng lượng
truyền nhận gói tin đa chặng, và được tách bạch rõ ràng giữa radio_energy_consumed_j và basal_energy_consumed_j.
"""

import os
import sys
import copy
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from core.network import WirelessSensorNetwork
from simulation.simulator import WSNSimulator
from topology.deployment import deploy_sensors, create_sink
from experiments.run_comprehensive_experiments import get_base_config


def run_lnd_for_model(label: str, algo: str, lb_overrides: dict, basal_j: float = 0.002, max_rounds: int = 1200):
    t0 = time.time()
    cfg = get_base_config(seed=42)
    cfg["energy"]["idle_energy_per_round_j"] = basal_j
    cfg["routing"]["algorithm"] = algo
    cfg["routing"]["lb_ecmhr"]["route_update_interval_rounds"] = 4
    cfg["routing"]["lb_ecmhr"].update(lb_overrides)

    sensors = deploy_sensors(cfg)
    sink = create_sink(cfg)
    net = WirelessSensorNetwork(sensors=sensors, sink=sink)
    net.build_topology()

    sim = WSNSimulator(network=net, config=cfg, routing_algorithm=algo)

    for r in range(1, max_rounds + 1):
        if sim.lnd_round is not None:
            break
        if sim.zero_connectivity_round is not None:
            sim.route_manager.route_update_interval_rounds = 10000
        sim.run_round()

    m = sim.get_metrics()

    # Kiểm chứng nghiêm ngặt tính đơn điệu
    alive_seq = [entry["alive_nodes"] for entry in sim.history]
    dead_seq = [entry["dead_nodes"] for entry in sim.history]
    assert all(alive_seq[i] <= alive_seq[i - 1] for i in range(1, len(alive_seq))), (
        f"Lỗi phi lý: alive_nodes không đơn điệu giảm trong {label}!"
    )
    assert all(dead_seq[i] >= dead_seq[i - 1] for i in range(1, len(dead_seq))), (
        f"Lỗi phi lý: dead_nodes không đơn điệu tăng trong {label}!"
    )

    fnd_mib = round((m["delivered_bytes_at_fnd"] or 0) / (1024 ** 2), 3)
    hnd_mib = round((m["delivered_bytes_at_hnd"] or 0) / (1024 ** 2), 3)
    lnd_mib = round((m["delivered_bytes_at_lnd"] or 0) / (1024 ** 2), 3)
    radio_eff = round((m["delivered_bytes"] * 8) / m["radio_energy_consumed_j"], 1) if m["radio_energy_consumed_j"] > 0 else 0.0

    slim_history = []
    for h in sim.history:
        slim_history.append({
            "round": h["round"],
            "alive_nodes": h["alive_nodes"],
            "dead_nodes": h["dead_nodes"],
            "low_energy_nodes": h["low_energy_nodes"],
            "total_energy_consumed_j": round(h["total_energy_consumed_j"], 3),
            "radio_energy_consumed_j": round(h.get("radio_energy_consumed_j", 0.0), 3),
            "basal_energy_consumed_j": round(h.get("basal_energy_consumed_j", 0.0), 3),
            "total_remaining_energy_j": round(h["total_remaining_energy_j"], 3),
            "physical_connectivity_ratio": round(h["physical_connectivity_ratio"], 4),
            "routing_connectivity_ratio": round(h["routing_connectivity_ratio"], 4),
            "delivered_data_mib": round(h["delivered_data_mb"], 4),
            "pdr": round(h["pdr"], 4),
            "delivered_packets": h["delivered_packets"],
            "generated_packets": h["generated_packets"]
        })

    res = {
        "label": label,
        "algorithm": algo,
        "basal_energy_j_per_round": basal_j,
        "rounds_completed": sim.current_round,
        "fnd_round": sim.fnd_round,
        "hnd_round": sim.hnd_round,
        "lnd_round": sim.lnd_round,
        "first_disconnection_round": sim.first_disconnection_round,
        "connectivity_90_round": sim.connectivity_90_round,
        "connectivity_50_round": sim.connectivity_50_round,
        "functional_50_round": sim.functional_50_round,
        "zero_connectivity_round": sim.zero_connectivity_round,
        "delivered_data_at_fnd_mib": fnd_mib,
        "delivered_data_at_hnd_mib": hnd_mib,
        "delivered_data_at_lnd_mib": lnd_mib,
        "delivered_packets_at_fnd": m["delivered_packets_at_fnd"],
        "delivered_packets_at_hnd": m["delivered_packets_at_hnd"],
        "delivered_packets_at_lnd": m["delivered_packets_at_lnd"],
        "total_energy_consumed_j": round(m["total_energy_consumed_j"], 2),
        "radio_energy_consumed_j": round(m["radio_energy_consumed_j"], 2),
        "basal_energy_consumed_j": round(m["basal_energy_consumed_j"], 2),
        "energy_efficiency_bits_per_j": round(m["energy_efficiency_bits_per_j"], 1),
        "radio_efficiency_bits_per_j": radio_eff,
        "history": slim_history
    }
    print(
        f"[OK] {label:24s} hoàn tất trong {time.time() - t0:.2f}s | "
        f"FND={sim.fnd_round}, HND={sim.hnd_round}, LND={sim.lnd_round}, Func50={sim.functional_50_round} | "
        f"Data@FND={fnd_mib} MiB, Data@LND={lnd_mib} MiB | RadioE={res['radio_energy_consumed_j']}J, BasalE={res['basal_energy_consumed_j']}J"
    )
    return res


def main():
    print("=" * 72)
    print("  CHẠY THỰC NGHIỆM VÒNG ĐỜI TOÀN DIỆN TỚI KHI ĐẠT LND (100% NÚT CHẾT)")
    print("=" * 72)

    minhop_res = run_lnd_for_model("Minimum-Hop", "minimum_hop", {}, basal_j=0.002, max_rounds=1200)
    ec_only_res = run_lnd_for_model(
        "EC-only (Hard a=0.20)",
        "lb_ecmhr",
        {"load_balancing_enabled": False, "allow_low_energy_fallback": False, "max_extra_hops": 0},
        basal_j=0.002,
        max_rounds=1200
    )
    lbecmhr_res = run_lnd_for_model(
        "LB-ECMHR (Hard a=0.20)",
        "lb_ecmhr",
        {"load_balancing_enabled": True, "allow_low_energy_fallback": False, "max_extra_hops": 1},
        basal_j=0.002,
        max_rounds=1200
    )
    lbecmhr_soft_res = run_lnd_for_model(
        "LB-ECMHR (Soft a=0.20->0.02)",
        "lb_ecmhr",
        {"load_balancing_enabled": True, "allow_low_energy_fallback": True, "soft_energy_threshold_ratio": 0.02, "max_extra_hops": 1},
        basal_j=0.002,
        max_rounds=1200
    )

    out_dir = os.path.join(ROOT_DIR, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "compare_routing_lnd.json")

    payload = {
        "minimum_hop": minhop_res,
        "ec_only": ec_only_res,
        "lb_ecmhr": lbecmhr_res,
        "lb_ecmhr_soft": lbecmhr_soft_res
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"[*] Đã lưu dữ liệu LND vào: {out_path}")


if __name__ == "__main__":
    main()
