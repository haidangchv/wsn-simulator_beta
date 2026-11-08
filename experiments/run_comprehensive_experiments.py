"""
Script: run_comprehensive_experiments.py
Mô tả: Thực hiện toàn bộ các thí nghiệm nghiên cứu WSN LB-ECMHR theo đúng các yêu cầu rà soát học thuật (Phương án B):
  - Part A: So sánh chi tiết 4 mô hình trên Seed 42 (100 rounds):
      1. Minimum-Hop (Baseline)
      2. EC-only (True Energy-Constrained Minimum-Hop, alpha=0.20, không cân bằng tải)
      3. LB-ECMHR (Hard Threshold alpha=0.20)
      4. LB-ECMHR (Soft Reserve Fallback alpha=0.20 -> 0.02)
  - Part B: Kiểm chứng độ vững chắc đa seed trên 10 seeds (42, 101, 2024, 7, 19, 55, 88, 123, 256, 999)
      kèm thống kê Mean ± Std và Paired Difference (Delta = LB - MinHop).
  - Part C: Phân tích độ nhạy 5 tham số (alpha, W, beta, gamma, delta_h) trên cùng cấu hình chuẩn.
  - Part D: Nghiên cứu bóc tách thành phần (Ablation Study - 6 cấu hình từ Minimum-Hop tới LB-ECMHR Soft).
  - Part E: Phân loại chi tiết nguyên nhân mất gói (tách NO_ROUTE_ENERGY_THRESHOLD và NO_ROUTE_PHYSICAL_PARTITION).
Toàn bộ kết quả được kiểm tra tính đơn điệu (monotonicity assertion) và lưu vào:
  - outputs/experiments_master_results.json
  - outputs/experiments_master_summary.csv
  - outputs/multiseed_comparison.csv
  - outputs/multiseed_paired_stats.json
"""

import os
import sys
import copy
import math
import json
import yaml
import time
import shutil
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

# Fix encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from core.network import WirelessSensorNetwork
from simulation.simulator import WSNSimulator
from topology.deployment import deploy_sensors, create_sink

SEEDS_10 = [42, 101, 2024, 7, 19, 55, 88, 123, 256, 999]


def get_base_config(seed=42):
    cfg_path = os.path.join(ROOT_DIR, "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg_clean = copy.deepcopy(cfg)
    cfg_clean["network"]["random_seed"] = seed
    cfg_clean["sensor"]["initial_energy_j"] = 2.0
    cfg_clean["sensor"]["transmission_range_m"] = 200
    cfg_clean["sensor"]["energy_threshold_ratio"] = 0.20
    cfg_clean["routing"]["energy_threshold_ratio"] = 0.20
    cfg_clean["packet"]["payload_size_bytes"] = 128
    cfg_clean["packet_crypto"]["enabled"] = False
    cfg_clean["environment"]["enabled"] = False  # Đánh giá thuần túy mạng / định tuyến
    cfg_clean["routing"]["algorithm"] = "lb_ecmhr"
    cfg_clean["routing"]["lb_ecmhr"] = {
        "load_window_rounds": 24,
        "overload_factor": 2.0,
        "recovery_factor": 1.2,
        "max_extra_hops": 1,
        "allow_overload_fallback": True,
        "route_update_interval_rounds": 1,
        "hysteresis_enabled": True,
        "load_balancing_enabled": True,
        "allow_low_energy_fallback": False,
        "soft_energy_threshold_ratio": 0.02,
        "candidate_routes_per_source": 6
    }
    return cfg_clean


def run_single_simulation(task):
    """
    Hàm worker chạy 1 kịch bản mô phỏng độc lập.
    task là dict chứa: experiment_id, name, config, algorithm, rounds, save_history
    """
    exp_id = task["experiment_id"]
    name = task["name"]
    cfg = task["config"]
    algo = task["algorithm"]
    rounds = task.get("rounds", 100)
    save_history = task.get("save_history", False)

    cache_dir = os.path.join(ROOT_DIR, "outputs", ".cache_runs_v2")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{exp_id}.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
            if (not save_history or "history" in cached_data) and "cumulative_relay_load_cv_all" in cached_data:
                return cached_data

    sensors = deploy_sensors(cfg)
    sink = create_sink(cfg)
    net = WirelessSensorNetwork(sensors=sensors, sink=sink)
    net.build_topology()

    sim = WSNSimulator(network=net, config=cfg, routing_algorithm=algo)
    sim.run(rounds=rounds)

    m = sim.get_metrics()

    # Kiểm tra tính đơn điệu của alive_nodes và dead_nodes
    alive_seq = [entry["alive_nodes"] for entry in sim.history]
    dead_seq = [entry["dead_nodes"] for entry in sim.history]
    assert all(alive_seq[i] <= alive_seq[i - 1] for i in range(1, len(alive_seq))), (
        f"Lỗi: alive_nodes không đơn điệu giảm trong kịch bản {exp_id} - {name}!"
    )
    assert all(dead_seq[i] >= dead_seq[i - 1] for i in range(1, len(dead_seq))), (
        f"Lỗi: dead_nodes không đơn điệu tăng trong kịch bản {exp_id} - {name}!"
    )

    # Tính CV trung bình theo thời gian (CV load average over rounds)
    window_cv_list = [entry.get("relay_load_cv") for entry in sim.history if entry.get("relay_load_cv") is not None]
    cv_mean = sum(window_cv_list) / len(window_cv_list) if window_cv_list else None

    # Forwarding packets của từng node
    forwarding_dict = {s.node_id: s.forwarded_packets for s in net.sensors}
    max_cum_forwarded = max(forwarding_dict.values()) if forwarding_dict else 0

    result = {
        "experiment_id": exp_id,
        "name": name,
        "algorithm": algo,
        "seed": cfg["network"]["random_seed"],
        "rounds": rounds,
        "generated_packets": m["generated_packets"],
        "delivered_packets": m["delivered_packets"],
        "dropped_packets": m["dropped_packets"],
        "pdr": round(m["pdr"] * 100, 2),
        "delivered_ratio_scheduled": round(m["delivered_ratio_scheduled"] * 100, 2),
        "delivered_data_mib": round(m["delivered_data_mb"], 3),
        "total_energy_consumed_j": round(m["total_energy_consumed_j"], 2),
        "radio_energy_consumed_j": round(m.get("radio_energy_consumed_j", m["total_energy_consumed_j"]), 2),
        "basal_energy_consumed_j": round(m.get("basal_energy_consumed_j", 0.0), 2),
        "energy_efficiency_bits_per_j": round(m["energy_efficiency_bits_per_j"], 1),
        "average_hop_count": round(m["average_hop_count"], 2),
        "full_conn_avg_hop_count": round(m.get("full_conn_avg_hop_count", m["average_hop_count"]), 2),
        "average_delay_ms": round(m["average_delay_ms"], 2),
        "full_conn_avg_delay_ms": round(m.get("full_conn_avg_delay_ms", m["average_delay_ms"]), 2),
        "throughput_bps": round(m["throughput_bps"], 2),
        "fnd_round": sim.fnd_round if sim.fnd_round is not None else "> 100",
        "fnd_numeric": sim.fnd_round if sim.fnd_round is not None else 101,
        "dead_nodes": m["dead_nodes"],
        "alive_nodes": m["alive_nodes"],
        "low_energy_nodes": m["low_energy_nodes"],
        "physical_connectivity_ratio": round(m["physical_connectivity_ratio"] * 100, 2),
        "routing_connectivity_ratio": round(m["routing_connectivity_ratio"] * 100, 2),
        "first_disconnection_round": m.get("first_disconnection_round"),
        "connectivity_50_round": m.get("connectivity_50_round"),
        "functional_50_round": m.get("functional_50_round") if m.get("functional_50_round") is not None else "> 100",
        "functional_50_numeric": m.get("functional_50_round") if m.get("functional_50_round") is not None else 101,
        "max_cumulative_forwarded": max_cum_forwarded,
        "relay_load_cv_final": round(m["relay_load_cv"], 3) if m["relay_load_cv"] is not None else None,
        "relay_load_cv_average": round(cv_mean, 3) if cv_mean is not None else None,
        "cumulative_relay_load_cv": round(m["cumulative_relay_load_cv"], 3) if m["cumulative_relay_load_cv"] is not None else None,
        "cumulative_relay_load_cv_all": round(m["cumulative_relay_load_cv_all"], 3) if m.get("cumulative_relay_load_cv_all") is not None else None,
        "cumulative_relay_load_cv_1hop": round(m["cumulative_relay_load_cv_1hop"], 3) if m.get("cumulative_relay_load_cv_1hop") is not None else None,
        "active_relay_count": m["active_relay_count"],
        "overloaded_relay_count": m["overloaded_relay_count"],
        "overload_transitions_count": m.get("overload_transitions_count", 0),
        "total_overload_node_rounds": m.get("total_overload_node_rounds", 0),
        "detour_route_count": m.get("detour_route_count", 0),
        "total_detour_packets": m.get("total_detour_packets", 0),
        "overload_fallback_route_count": m.get("overload_fallback_route_count", 0),
        "soft_fallback_route_count": m.get("soft_fallback_route_count", 0),
        "total_soft_fallback_packets": m.get("total_soft_fallback_packets", 0),
        "routing_reroutes": m.get("routing_reroutes", 0),
        "drop_source_dead": m.get("drop_source_dead", 0),
        "drop_no_route": m.get("drop_no_route", 0),
        "drop_no_route_energy": m.get("drop_no_route_energy", 0),
        "drop_no_route_partition": m.get("drop_no_route_partition", 0),
        "drop_tx_energy": m.get("drop_tx_energy", 0),
        "drop_rx_energy": m.get("drop_rx_energy", 0),
        "drop_crypto_auth": m.get("drop_crypto_auth", 0)
    }

    if save_history:
        result["history"] = sim.history
        result["forwarding"] = forwarding_dict

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, default=str)

    return result


def build_experiment_tasks():
    tasks = []

    # 1. Main comparison (Seed 42) - Lưu history đầy đủ cho cả 4 mô hình cốt lõi để vẽ biểu đồ
    base_cfg = get_base_config(seed=42)

    # 1a. Minimum-Hop
    cfg_minhop = copy.deepcopy(base_cfg)
    cfg_minhop["routing"]["algorithm"] = "minimum_hop"
    tasks.append({
        "experiment_id": "main_compare_minhop",
        "name": "Minimum-Hop (Seed 42)",
        "config": cfg_minhop,
        "algorithm": "minimum_hop",
        "rounds": 100,
        "save_history": True
    })

    # 1b. True EC-only (Alpha=0.20, No Load Balancing / No Rotation)
    cfg_ec = copy.deepcopy(base_cfg)
    cfg_ec["routing"]["lb_ecmhr"]["load_balancing_enabled"] = False
    cfg_ec["routing"]["lb_ecmhr"]["allow_low_energy_fallback"] = False
    cfg_ec["routing"]["lb_ecmhr"]["max_extra_hops"] = 0
    tasks.append({
        "experiment_id": "ablation_ec_only",
        "name": "Ablation 2: True EC-only (Alpha=0.20, No LB)",
        "config": cfg_ec,
        "algorithm": "lb_ecmhr",
        "rounds": 100,
        "save_history": True
    })

    # 1c. LB-ECMHR (Hard Threshold Alpha=0.20)
    cfg_lb_hard = copy.deepcopy(base_cfg)
    tasks.append({
        "experiment_id": "main_compare_lbecmhr",
        "name": "LB-ECMHR Hard (Alpha=0.20, Seed 42)",
        "config": cfg_lb_hard,
        "algorithm": "lb_ecmhr",
        "rounds": 100,
        "save_history": True
    })

    # 1d. LB-ECMHR (Soft Reserve Fallback Alpha=0.20 -> 0.02)
    cfg_lb_soft = copy.deepcopy(base_cfg)
    cfg_lb_soft["routing"]["lb_ecmhr"]["allow_low_energy_fallback"] = True
    cfg_lb_soft["routing"]["lb_ecmhr"]["soft_energy_threshold_ratio"] = 0.02
    tasks.append({
        "experiment_id": "main_compare_lbecmhr_soft",
        "name": "LB-ECMHR Soft Fallback (Alpha=0.20->0.02, Seed 42)",
        "config": cfg_lb_soft,
        "algorithm": "lb_ecmhr",
        "rounds": 100,
        "save_history": True
    })

    # 2. Multi-seed testing (10 Seeds: 42, 101, 2024, 7, 19, 55, 88, 123, 256, 999)
    for seed in SEEDS_10:
        if seed == 42:
            continue
        s_base = get_base_config(seed=seed)

        s_min = copy.deepcopy(s_base)
        s_min["routing"]["algorithm"] = "minimum_hop"
        tasks.append({
            "experiment_id": f"multiseed_minhop_s{seed}",
            "name": f"Minimum-Hop (Seed {seed})",
            "config": s_min,
            "algorithm": "minimum_hop",
            "rounds": 100,
            "save_history": False
        })

        s_lb_hard = copy.deepcopy(s_base)
        tasks.append({
            "experiment_id": f"multiseed_lbecmhr_s{seed}",
            "name": f"LB-ECMHR Hard (Seed {seed})",
            "config": s_lb_hard,
            "algorithm": "lb_ecmhr",
            "rounds": 100,
            "save_history": False
        })

        s_lb_soft = copy.deepcopy(s_base)
        s_lb_soft["routing"]["lb_ecmhr"]["allow_low_energy_fallback"] = True
        s_lb_soft["routing"]["lb_ecmhr"]["soft_energy_threshold_ratio"] = 0.02
        tasks.append({
            "experiment_id": f"multiseed_lbecmhr_soft_s{seed}",
            "name": f"LB-ECMHR Soft (Seed {seed})",
            "config": s_lb_soft,
            "algorithm": "lb_ecmhr",
            "rounds": 100,
            "save_history": False
        })

    # 3. Parametric Sensitivity Analysis (Cố định seed 42, các tham số khác giữ ở mức chuẩn)
    # 3.1. Exp 1: Alpha in [0.10, 0.15, 0.20, 0.25, 0.30]
    for alpha in [0.10, 0.15, 0.20, 0.25, 0.30]:
        cfg_alpha = copy.deepcopy(base_cfg)
        cfg_alpha["sensor"]["energy_threshold_ratio"] = alpha
        cfg_alpha["routing"]["energy_threshold_ratio"] = alpha
        tasks.append({
            "experiment_id": f"exp1_alpha_{int(alpha*100)}",
            "name": f"Exp1: Alpha = {alpha:.2f}",
            "config": cfg_alpha,
            "algorithm": "lb_ecmhr",
            "rounds": 100,
            "save_history": False
        })

    # 3.2. Exp 2: Load Window W in [6, 12, 24, 48]
    for w in [6, 12, 24, 48]:
        cfg_w = copy.deepcopy(base_cfg)
        cfg_w["routing"]["lb_ecmhr"]["load_window_rounds"] = w
        tasks.append({
            "experiment_id": f"exp2_w_{w}",
            "name": f"Exp2: Window W = {w}h",
            "config": cfg_w,
            "algorithm": "lb_ecmhr",
            "rounds": 100,
            "save_history": False
        })

    # 3.3. Exp 3: Overload factor Beta in [1.5, 2.0, 2.5, 3.0]
    for beta in [1.5, 2.0, 2.5, 3.0]:
        cfg_beta = copy.deepcopy(base_cfg)
        cfg_beta["routing"]["lb_ecmhr"]["overload_factor"] = beta
        cfg_beta["routing"]["lb_ecmhr"]["recovery_factor"] = min(1.2, beta - 0.3)
        tasks.append({
            "experiment_id": f"exp3_beta_{str(beta).replace('.', '')}",
            "name": f"Exp3: Beta = {beta:.1f}",
            "config": cfg_beta,
            "algorithm": "lb_ecmhr",
            "rounds": 100,
            "save_history": False
        })

    # 3.4. Exp 4: Recovery factor Gamma in [0.8, 1.0, 1.2, 1.5] (beta=2.0)
    for gamma in [0.8, 1.0, 1.2, 1.5]:
        cfg_gamma = copy.deepcopy(base_cfg)
        cfg_gamma["routing"]["lb_ecmhr"]["recovery_factor"] = gamma
        tasks.append({
            "experiment_id": f"exp4_gamma_{str(gamma).replace('.', '')}",
            "name": f"Exp4: Gamma = {gamma:.1f}",
            "config": cfg_gamma,
            "algorithm": "lb_ecmhr",
            "rounds": 100,
            "save_history": False
        })

    # 3.5. Exp 5: Max extra hops Delta_H in [0, 1, 2]
    for dh in [0, 1, 2]:
        cfg_dh = copy.deepcopy(base_cfg)
        cfg_dh["routing"]["lb_ecmhr"]["max_extra_hops"] = dh
        tasks.append({
            "experiment_id": f"exp5_deltah_{dh}",
            "name": f"Exp5: Delta_H = {dh}",
            "config": cfg_dh,
            "algorithm": "lb_ecmhr",
            "rounds": 100,
            "save_history": False
        })

    # 4. Additional Ablation Study configurations
    # Config 2b: LB-ECMHR without Overload Filter (beta = 999.0, keeps bottleneck/load tie-breaking)
    cfg_no_ovf = copy.deepcopy(base_cfg)
    cfg_no_ovf["routing"]["lb_ecmhr"]["overload_factor"] = 999.0
    tasks.append({
        "experiment_id": "ablation_no_overload_filter",
        "name": "Ablation 2b: LB-ECMHR (Beta=999, Tie-Break Only)",
        "config": cfg_no_ovf,
        "algorithm": "lb_ecmhr",
        "rounds": 100,
        "save_history": False
    })

    # Config 3: LB-ECMHR (Delta_H = 0 - cấm đi vòng)
    cfg_dh0 = copy.deepcopy(base_cfg)
    cfg_dh0["routing"]["lb_ecmhr"]["max_extra_hops"] = 0
    tasks.append({
        "experiment_id": "ablation_lb_dh0",
        "name": "Ablation 3: LB-ECMHR (Delta_H = 0)",
        "config": cfg_dh0,
        "algorithm": "lb_ecmhr",
        "rounds": 100,
        "save_history": False
    })

    # Config 4: LB-ECMHR (Không Hysteresis - tắt hysteresis hoàn toàn)
    cfg_nohys = copy.deepcopy(base_cfg)
    cfg_nohys["routing"]["lb_ecmhr"]["hysteresis_enabled"] = False
    cfg_nohys["routing"]["lb_ecmhr"]["recovery_factor"] = 2.0
    cfg_nohys["routing"]["lb_ecmhr"]["overload_factor"] = 2.0
    tasks.append({
        "experiment_id": "ablation_no_hysteresis",
        "name": "Ablation 4: LB-ECMHR (No Hysteresis)",
        "config": cfg_nohys,
        "algorithm": "lb_ecmhr",
        "rounds": 100,
        "save_history": False
    })

    return tasks


def main():
    t_start = time.time()
    print("=" * 70)
    print("  WSN LB-ECMHR: CHƯƠNG TRÌNH THỰC NGHIỆM TỔNG THỂ & CHUẨN HÓA DỮ LIỆU")
    print("=" * 70)

    tasks = build_experiment_tasks()
    print(f"[*] Tổng số kịch bản cần thực nghiệm: {len(tasks)}")
    print(f"[*] Hệ thống có {os.cpu_count()} CPU cores. Khởi động ProcessPoolExecutor...")

    results_by_id = {}
    summary_rows = []

    max_workers = min(6, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(run_single_simulation, task): task
            for task in tasks
        }

        completed_count = 0
        for future in as_completed(future_to_task):
            task_info = future_to_task[future]
            completed_count += 1
            try:
                res = future.result()
                results_by_id[res["experiment_id"]] = res
                summary_rows.append({k: v for k, v in res.items() if k not in ["history", "forwarding"]})
                print(
                    f"[{completed_count:02d}/{len(tasks)}] Xong: {res['name']:42s} | "
                    f"PDR: {res['pdr']:5.2f}% | Sched: {res['delivered_ratio_scheduled']:5.2f}% | "
                    f"Dead: {res['dead_nodes']:2d} | Func50: {str(res['functional_50_round']):5s}"
                )
            except Exception as e:
                print(f"[!] Lỗi khi chạy kịch bản {task_info['name']}: {e}")
                raise e

    print(f"\n[*] Tất cả kịch bản hoàn tất sau {time.time() - t_start:.2f} giây.")

    # -------------------------------------------------------------
    # Tổng hợp bảng Multi-Seed Comparison (10 Seeds + Paired Differences)
    # -------------------------------------------------------------
    multiseed_records = []
    runs_by_model = {}

    model_specs = [
        ("MINIMUM_HOP", "main_compare_minhop", "multiseed_minhop_s"),
        ("LB_ECMHR_HARD", "main_compare_lbecmhr", "multiseed_lbecmhr_s"),
        ("LB_ECMHR_SOFT", "main_compare_lbecmhr_soft", "multiseed_lbecmhr_soft_s"),
    ]

    for label, seed42_key, prefix in model_specs:
        algo_runs = []
        for s in SEEDS_10:
            key = seed42_key if s == 42 else f"{prefix}{s}"
            algo_runs.append(results_by_id[key])
        runs_by_model[label] = algo_runs

        pdr_vals = [r["pdr"] for r in algo_runs]
        sched_vals = [r["delivered_ratio_scheduled"] for r in algo_runs]
        data_vals = [r["delivered_data_mib"] for r in algo_runs]
        e_vals = [r["total_energy_consumed_j"] for r in algo_runs]
        eff_vals = [r["energy_efficiency_bits_per_j"] for r in algo_runs]
        hop_vals = [r["average_hop_count"] for r in algo_runs]
        hop_full_vals = [r["full_conn_avg_hop_count"] for r in algo_runs]
        delay_vals = [r["average_delay_ms"] for r in algo_runs]
        dead_vals = [r["dead_nodes"] for r in algo_runs]
        fnd_vals = [r["fnd_numeric"] for r in algo_runs]
        func50_vals = [r["functional_50_numeric"] for r in algo_runs]
        phys_conn_vals = [r["physical_connectivity_ratio"] for r in algo_runs]
        rout_conn_vals = [r["routing_connectivity_ratio"] for r in algo_runs]
        max_load_vals = [r["max_cumulative_forwarded"] for r in algo_runs]
        cv_all_vals = [r["cumulative_relay_load_cv_all"] for r in algo_runs]
        cv_1hop_vals = [r["cumulative_relay_load_cv_1hop"] for r in algo_runs]

        multiseed_records.append({
            "algorithm": label,
            "n_seeds": len(SEEDS_10),
            "pdr_mean": round(float(pd.Series(pdr_vals).mean()), 2),
            "pdr_std": round(float(pd.Series(pdr_vals).std()), 2),
            "sched_ratio_mean": round(float(pd.Series(sched_vals).mean()), 2),
            "sched_ratio_std": round(float(pd.Series(sched_vals).std()), 2),
            "data_mib_mean": round(float(pd.Series(data_vals).mean()), 3),
            "data_mib_std": round(float(pd.Series(data_vals).std()), 3),
            "energy_j_mean": round(float(pd.Series(e_vals).mean()), 2),
            "energy_j_std": round(float(pd.Series(e_vals).std()), 2),
            "energy_eff_mean": round(float(pd.Series(eff_vals).mean()), 1),
            "energy_eff_std": round(float(pd.Series(eff_vals).std()), 1),
            "hop_mean": round(float(pd.Series(hop_vals).mean()), 2),
            "hop_std": round(float(pd.Series(hop_vals).std()), 2),
            "hop_full_conn_mean": round(float(pd.Series(hop_full_vals).mean()), 2),
            "hop_full_conn_std": round(float(pd.Series(hop_full_vals).std()), 2),
            "delay_ms_mean": round(float(pd.Series(delay_vals).mean()), 2),
            "delay_ms_std": round(float(pd.Series(delay_vals).std()), 2),
            "dead_nodes_mean": round(float(pd.Series(dead_vals).mean()), 1),
            "dead_nodes_std": round(float(pd.Series(dead_vals).std()), 1),
            "fnd_mean": round(float(pd.Series(fnd_vals).mean()), 1),
            "fnd_std": round(float(pd.Series(fnd_vals).std()), 1),
            "func50_mean": round(float(pd.Series(func50_vals).mean()), 1),
            "func50_std": round(float(pd.Series(func50_vals).std()), 1),
            "physical_conn_mean": round(float(pd.Series(phys_conn_vals).mean()), 2),
            "physical_conn_std": round(float(pd.Series(phys_conn_vals).std()), 2),
            "routing_conn_mean": round(float(pd.Series(rout_conn_vals).mean()), 2),
            "routing_conn_std": round(float(pd.Series(rout_conn_vals).std()), 2),
            "max_load_mean": round(float(pd.Series(max_load_vals).mean()), 1),
            "max_load_std": round(float(pd.Series(max_load_vals).std()), 1),
            "cv_all_mean": round(float(pd.Series(cv_all_vals).mean()), 3),
            "cv_all_std": round(float(pd.Series(cv_all_vals).std()), 3),
            "cv_1hop_mean": round(float(pd.Series(cv_1hop_vals).mean()), 3),
            "cv_1hop_std": round(float(pd.Series(cv_1hop_vals).std()), 3),
        })

    # Compute paired differences (Delta = LB - MinHop) per seed
    paired_stats = {}
    for target_label in ["LB_ECMHR_HARD", "LB_ECMHR_SOFT"]:
        deltas = {
            "dead_nodes": [],
            "fnd_numeric": [],
            "functional_50_numeric": [],
            "pdr": [],
            "delivered_ratio_scheduled": [],
            "delivered_data_mib": [],
            "total_energy_consumed_j": [],
            "energy_efficiency_bits_per_j": [],
            "max_cumulative_forwarded": [],
            "cumulative_relay_load_cv_all": [],
            "cumulative_relay_load_cv_1hop": []
        }
        for r_min, r_lb in zip(runs_by_model["MINIMUM_HOP"], runs_by_model[target_label]):
            for metric_key in deltas:
                deltas[metric_key].append(r_lb[metric_key] - r_min[metric_key])

        paired_stats[target_label] = {
            k: {
                "mean_delta": round(float(pd.Series(v).mean()), 3),
                "std_delta": round(float(pd.Series(v).std()), 3),
                "min_delta": round(float(min(v)), 3),
                "max_delta": round(float(max(v)), 3)
            }
            for k, v in deltas.items()
        }

    out_dir = os.path.join(ROOT_DIR, "outputs")
    os.makedirs(out_dir, exist_ok=True)

    df_multiseed = pd.DataFrame(multiseed_records)
    multiseed_path = os.path.join(out_dir, "multiseed_comparison.csv")
    df_multiseed.to_csv(multiseed_path, index=False, encoding="utf-8")
    print(f"[*] Đã xuất bảng so sánh đa seed (10 seeds): {multiseed_path}")

    paired_path = os.path.join(out_dir, "multiseed_paired_stats.json")
    with open(paired_path, "w", encoding="utf-8") as f:
        json.dump(paired_stats, f, indent=2, ensure_ascii=False)
    print(f"[*] Đã xuất thống kê ghép cặp (Paired Differences): {paired_path}")

    # -------------------------------------------------------------
    # Lưu Master JSON và Master CSV
    # -------------------------------------------------------------
    master_json_path = os.path.join(out_dir, "experiments_master_results.json")
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(results_by_id, f, indent=2, ensure_ascii=False, default=str)
    print(f"[*] Đã xuất Master JSON: {master_json_path}")

    df_summary = pd.DataFrame(summary_rows)
    master_csv_path = os.path.join(out_dir, "experiments_master_summary.csv")
    df_summary.to_csv(master_csv_path, index=False, encoding="utf-8")
    print(f"[*] Đã xuất Master CSV: {master_csv_path}")

    # Đồng bộ file compare_routing_100_rounds.json chứa cả 4 mô hình chính
    legacy_json_path = os.path.join(out_dir, "compare_routing_100_rounds.json")
    legacy_data = {
        "minimum_hop": results_by_id["main_compare_minhop"],
        "ec_only": results_by_id["ablation_ec_only"],
        "lb_ecmhr": results_by_id["main_compare_lbecmhr"],
        "lb_ecmhr_soft": results_by_id["main_compare_lbecmhr_soft"]
    }
    with open(legacy_json_path, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"[*] Đã đồng bộ file: {legacy_json_path}")

    print("\n" + "=" * 70)
    print("  KẾT QUẢ THỰC NGHIỆM ĐÃ ĐƯỢC CHUẨN HÓA VÀ XÁC THỰC THÀNH CÔNG!")
    print("=" * 70)


if __name__ == "__main__":
    main()
