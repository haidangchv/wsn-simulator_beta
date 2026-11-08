"""
Script: generate_report_charts.py
Mô tả: Tự động vẽ 6 biểu đồ so sánh thực nghiệm Kịch bản A (100 rounds) và sơ đồ minh họa Hình 4
phục vụ báo cáo chuyên đề LB-ECMHR theo chuẩn xuất bản (PNG 300 DPI).
Dữ liệu nạp trực tiếp từ outputs/compare_routing_100_rounds.json (bao gồm Minimum-Hop, EC-only,
LB-ECMHR Hard Threshold và LB-ECMHR Soft Fallback).
"""

import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 11.5
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 8.6
plt.rcParams['figure.titlesize'] = 12.5

COLOR_MINHOP = '#d9534f'   # Đỏ cam coral - Minimum-Hop
COLOR_ECONLY = '#7f8c8d'   # Xám đậm - EC-only (No LB)
COLOR_LBHARD = '#1b7837'   # Xanh lục bảo đậm - LB-ECMHR (Hard)
COLOR_LBSOFT = '#1f78b4'   # Xanh dương đậm - LB-ECMHR (Soft Fallback)
COLOR_WARN = '#e67e22'

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "outputs", "compare_routing_100_rounds.json")


def load_simulation_data():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Chưa tìm thấy file dữ liệu thực nghiệm: {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_chart1_fnd_comparison(data):
    """Hình 6 (Biểu đồ 1): So sánh cột mốc FND, Functional Lifetime (Func50) và số nút chết sau 100 rounds"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.5), gridspec_kw={'width_ratios': [1.35, 1]})

    algos = [
        'Minimum-Hop\n(Baseline)',
        'EC-only\n(Hard α=0.20, No LB)',
        'LB-ECMHR\n(Hard α=0.20)',
        'LB-ECMHR\n(Soft α=0.20→0.02)'
    ]
    fnd_vals = [21, 100, 100, 100]
    func50_vals = [
        data['minimum_hop']['functional_50_numeric'],
        data['ec_only']['functional_50_numeric'],
        data['lb_ecmhr']['functional_50_numeric'],
        data['lb_ecmhr_soft']['functional_50_numeric']
    ]
    y = np.arange(len(algos))
    h = 0.34

    ax1.barh(y + h/2, fnd_vals, height=h, color=[COLOR_MINHOP, COLOR_ECONLY, COLOR_LBHARD, COLOR_LBSOFT],
             edgecolor='black', linewidth=1.0, alpha=0.92, label='FND (Round có nút chết đầu tiên)')
    ax1.barh(y - h/2, func50_vals, height=h, color=['#f5b7b1', '#d5dbdb', '#a9dfbf', '#aed6f1'],
             edgecolor='black', linewidth=1.0, hatch='//', alpha=0.92, label='Func50 (Round còn ≥ 50% cảm biến kết nối Sink)')

    ax1.set_yticks(y)
    ax1.set_yticklabels(algos)
    ax1.set_xlim(0, 122)
    ax1.set_xlabel('Chu kỳ mô phỏng (Round)')
    ax1.set_title('Cột mốc FND và Tuổi thọ Hữu ích (Func50)', pad=10)
    ax1.grid(axis='x', linestyle=':', alpha=0.6)
    ax1.axvline(x=100, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax1.legend(loc='lower right', fontsize=8.2, framealpha=0.95)

    for i, (fv, fnv) in enumerate(zip(fnd_vals, func50_vals)):
        f_txt = f"FND = R{fv}" if fv < 100 else "FND > 100 (0 chết)"
        ax1.text(fv + 1.5, i + h/2, f_txt, va='center', fontsize=8.3, fontweight='bold')
        ax1.text(fnv + 1.5, i - h/2, f"Func50 = R{fnv}", va='center', fontsize=8.3, color='#2c3e50', fontweight='bold')

    # Subplot 2: Số nút chết tại Round 100
    dead_vals = [
        data['minimum_hop']['dead_nodes'],
        data['ec_only']['dead_nodes'],
        data['lb_ecmhr']['dead_nodes'],
        data['lb_ecmhr_soft']['dead_nodes']
    ]
    colors = [COLOR_MINHOP, COLOR_ECONLY, COLOR_LBHARD, COLOR_LBSOFT]
    ax2.bar(algos, dead_vals, color=colors, width=0.48, edgecolor='black', linewidth=1.1, alpha=0.9)
    ax2.set_ylim(0, 75)
    ax2.set_ylabel('Số nút chết (Dead Nodes)')
    ax2.set_title('Số nút chết sau 100 Rounds (Kịch bản A)', pad=10)
    ax2.grid(axis='y', linestyle=':', alpha=0.6)
    ax2.tick_params(axis='x', labelsize=8.3)

    for i, dv in enumerate(dead_vals):
        pct = dv / 5.0
        ax2.text(i, dv + 2.2, f'{dv} nút\n({pct:.1f}%)', ha='center', fontweight='bold',
                 color=colors[i], fontsize=8.6)

    plt.suptitle('Hình 6. So Sánh Cột Mốc FND, Tuổi Thọ Chức Năng (Func50) và Số Lượng Nút Chết (100 Rounds)', y=1.02, fontsize=12, fontweight='bold')
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart1_fnd_comparison.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def plot_chart2_alive_nodes(data):
    """Hình 7 (Biểu đồ 2): Số lượng nút còn sống theo round - Kiểm chứng nghiêm ngặt tính đơn điệu"""
    h_min = data['minimum_hop']['history']
    h_lb = data['lb_ecmhr']['history']
    h_soft = data['lb_ecmhr_soft']['history']

    rounds_min = [item['round'] for item in h_min]
    alive_min = [item['alive_nodes'] for item in h_min]
    alive_lb = [item['alive_nodes'] for item in h_lb]
    alive_soft = [item['alive_nodes'] for item in h_soft]

    assert all(alive_min[i] <= alive_min[i - 1] for i in range(1, len(alive_min)))
    assert all(alive_lb[i] <= alive_lb[i - 1] for i in range(1, len(alive_lb)))
    assert all(alive_soft[i] <= alive_soft[i - 1] for i in range(1, len(alive_soft)))

    r_plot = [0] + rounds_min
    a_min_plot = [500] + alive_min
    a_lb_plot = [500] + alive_lb
    a_soft_plot = [500] + alive_soft

    fig, ax = plt.subplots(figsize=(9.0, 4.8))

    ax.step(r_plot, a_lb_plot, where='post', color=COLOR_LBHARD, linewidth=2.8,
            label='LB-ECMHR Hard (α=0.20) & EC-only: Bảo toàn 500/500 nút (0 nút chết)')
    ax.step(r_plot, a_soft_plot, where='post', color=COLOR_LBSOFT, linewidth=2.2, linestyle='--',
            label='LB-ECMHR Soft Fallback (α=0.20→0.02): Bảo toàn 500/500 nút (0 nút chết)')
    ax.step(r_plot, a_min_plot, where='post', color=COLOR_MINHOP, linewidth=2.4,
            label='Minimum-Hop (Baseline): Giảm đơn điệu xuống 440 nút (60 nút chết)')

    ax.fill_between(r_plot, a_min_plot, a_lb_plot, step='post', color=COLOR_LBHARD, alpha=0.13,
                    label='Vùng bảo tồn phần cứng mạng (+60 cảm biến sống)')

    ax.plot(21, 499, marker='o', markersize=8, color=COLOR_WARN, markeredgecolor='black', markeredgewidth=1.2)
    ax.annotate('FND = Round 21 (Minimum-Hop)\nNút relay 1-hop đầu tiên cạn pin',
                xy=(21, 499), xytext=(28, 474),
                arrowprops=dict(arrowstyle="->", color=COLOR_WARN, lw=1.6),
                bbox=dict(boxstyle="round,pad=0.35", fc="lightyellow", ec=COLOR_WARN, lw=1.2),
                fontweight='bold', fontsize=8.6)

    ax.plot(100, 440, marker='s', markersize=7, color=COLOR_MINHOP, markeredgecolor='black')
    ax.annotate('Round 100: 440 nút sống\n(Kiểm chứng đơn điệu: alive[t] ≤ alive[t-1])',
                xy=(100, 440), xytext=(58, 416),
                arrowprops=dict(arrowstyle="->", color=COLOR_MINHOP, lw=1.5),
                bbox=dict(boxstyle="round,pad=0.3", fc="#ffebee", ec=COLOR_MINHOP, lw=1),
                fontsize=8.4, fontweight='bold', color=COLOR_MINHOP)

    ax.set_xlim(0, 105)
    ax.set_ylim(400, 520)
    ax.set_xlabel('Chu kỳ mô phỏng (Round - 1 round = 1 giờ)')
    ax.set_ylabel('Số lượng nút cảm biến còn sống (Alive Nodes)')
    ax.set_title('Hình 7. Số Lượng Nút Cảm Biến Còn Sống Theo Round (Alive Nodes vs Round)', pad=12)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='lower left', framealpha=0.95)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart2_alive_nodes_vs_round.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def plot_chart3_energy(data):
    """Hình 8 (Biểu đồ 3): Tổng năng lượng tiêu thụ, năng lượng còn lại và hiệu suất bit/J sau 100 rounds"""
    h_min = data['minimum_hop']['history']
    h_ec = data['ec_only']['history']
    h_lb = data['lb_ecmhr']['history']
    h_soft = data['lb_ecmhr_soft']['history']

    rounds = [0] + [item['round'] for item in h_min]
    e_rem_min = [1000.0] + [item['total_remaining_energy_j'] for item in h_min]
    e_rem_ec = [1000.0] + [item['total_remaining_energy_j'] for item in h_ec]
    e_rem_lb = [1000.0] + [item['total_remaining_energy_j'] for item in h_lb]
    e_rem_soft = [1000.0] + [item['total_remaining_energy_j'] for item in h_soft]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.6), gridspec_kw={'width_ratios': [1.22, 1]})

    ax1.plot(rounds, e_rem_lb, color=COLOR_LBHARD, linewidth=2.5,
             label=f"LB-ECMHR Hard (Còn {e_rem_lb[-1]:.1f} J | Tiêu thụ {data['lb_ecmhr']['total_energy_consumed_j']:.1f} J)")
    ax1.plot(rounds, e_rem_ec, color=COLOR_ECONLY, linewidth=2.0, linestyle='-.',
             label=f"EC-only No LB (Còn {e_rem_ec[-1]:.1f} J | Tiêu thụ {data['ec_only']['total_energy_consumed_j']:.1f} J)")
    ax1.plot(rounds, e_rem_soft, color=COLOR_LBSOFT, linewidth=2.4, linestyle='-',
             label=f"LB-ECMHR Soft (Còn {e_rem_soft[-1]:.1f} J | Tiêu thụ {data['lb_ecmhr_soft']['total_energy_consumed_j']:.1f} J)")
    ax1.plot(rounds, e_rem_min, color=COLOR_MINHOP, linewidth=2.2, linestyle='--',
             label=f"Minimum-Hop (Còn {e_rem_min[-1]:.1f} J | Tiêu thụ {data['minimum_hop']['total_energy_consumed_j']:.1f} J)")

    ax1.set_xlim(0, 100)
    ax1.set_ylim(680, 1020)
    ax1.set_xlabel('Chu kỳ mô phỏng (Round)')
    ax1.set_ylabel('Tổng năng lượng còn lại toàn mạng (Joules)')
    ax1.set_title('Diễn biến Năng lượng Còn lại (Remaining Energy)', pad=10)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='lower left', framealpha=0.95, fontsize=8.0)

    # Panel 2: So sánh Năng lượng tiêu thụ (J) và Hiệu suất năng lượng (kbit/J)
    algos = ['Minimum-Hop', 'EC-only\n(No LB)', 'LB-ECMHR\n(Hard)', 'LB-ECMHR\n(Soft)']
    e_vals = [
        data['minimum_hop']['total_energy_consumed_j'],
        data['ec_only']['total_energy_consumed_j'],
        data['lb_ecmhr']['total_energy_consumed_j'],
        data['lb_ecmhr_soft']['total_energy_consumed_j']
    ]
    eff_kbit = [
        data['minimum_hop']['energy_efficiency_bits_per_j'] / 1000.0,
        data['ec_only']['energy_efficiency_bits_per_j'] / 1000.0,
        data['lb_ecmhr']['energy_efficiency_bits_per_j'] / 1000.0,
        data['lb_ecmhr_soft']['energy_efficiency_bits_per_j'] / 1000.0
    ]
    colors = [COLOR_MINHOP, COLOR_ECONLY, COLOR_LBHARD, COLOR_LBSOFT]
    bars = ax2.bar(algos, e_vals, color=colors, width=0.46, edgecolor='black', linewidth=1.1, alpha=0.9)
    ax2.set_ylim(0, 360)
    ax2.set_ylabel('Tổng năng lượng tiêu thụ (Joules)')
    ax2.set_title('Tiêu thụ Năng lượng & Hiệu suất (kbit/J)', pad=10)
    ax2.grid(axis='y', linestyle=':', alpha=0.6)

    for i, (ev, ef) in enumerate(zip(e_vals, eff_kbit)):
        ax2.text(i, ev + 6, f"{ev:.1f} J\n({ef:.1f} kb/J)", ha='center', fontweight='bold', color=colors[i], fontsize=8.3)

    plt.suptitle('Hình 8. Tổng Năng Lượng Tiêu Thụ, Năng Lượng Còn Lại và Hiệu Suất Truyền Tải (bit/J)', y=1.02, fontsize=12, fontweight='bold')
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart3_energy_consumption.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def plot_chart4_connectivity(data):
    """
    Hình 9 (Biểu đồ 4): Phân biệt rõ Kết nối Vật lý C_physical(t) và Kết nối Định tuyến C_routing(t)
    cho cả 4 mô hình: Minimum-Hop, EC-only, LB-ECMHR Hard (α=0.20) và LB-ECMHR Soft Fallback (α=0.20→0.02).
    """
    h_min = data['minimum_hop']['history']
    h_ec = data['ec_only']['history']
    h_lb = data['lb_ecmhr']['history']
    h_soft = data['lb_ecmhr_soft']['history']

    rounds = [0] + [item['round'] for item in h_min]

    lb_phys = [100.0] + [item.get('physical_connectivity_ratio', 1.0) * 100 for item in h_lb]
    ec_rout = [100.0] + [item.get('routing_connectivity_ratio', 1.0) * 100 for item in h_ec]
    lb_rout = [100.0] + [item.get('routing_connectivity_ratio', 1.0) * 100 for item in h_lb]
    soft_rout = [100.0] + [item.get('routing_connectivity_ratio', 1.0) * 100 for item in h_soft]
    min_rout = [100.0] + [item.get('routing_connectivity_ratio', 1.0) * 100 for item in h_min]

    fig, ax = plt.subplots(figsize=(9.8, 5.3))

    ax.plot(rounds, lb_phys, color='#27ae60', linewidth=2.8, linestyle='-',
            label='LB-ECMHR (Hard & Soft) & EC-only: C_physical(t) = 100% suốt 100 rounds (0 nút chết)')
    ax.plot(rounds, soft_rout, color=COLOR_LBSOFT, linewidth=2.6, linestyle='-',
            label='LB-ECMHR Soft Fallback (α=0.20→0.02): C_routing(t) duy trì ≥50% tới Round 96 (Vượt Min-Hop!)')
    ax.plot(rounds, min_rout, color=COLOR_MINHOP, linewidth=2.3, linestyle='--',
            label='Minimum-Hop: C_physical(t) ≡ C_routing(t) (Sập xuống 1.8% tại Round 92 do relay chết)')
    ax.plot(rounds, lb_rout, color=COLOR_LBHARD, linewidth=2.2, linestyle='-.',
            label='LB-ECMHR Hard (α=0.20): C_routing(t) giảm tại Round 79 (Bảo lưu cứng 20% pin)')
    ax.plot(rounds, ec_rout, color=COLOR_ECONLY, linewidth=1.9, linestyle=':',
            label='EC-only (Hard α=0.20, No LB): C_routing(t) giảm sớm từ Round 73 do thiếu cân bằng tải')

    ax.axhline(y=50.0, color='gray', linestyle=':', linewidth=1.1, alpha=0.7)
    ax.text(3, 52, 'Ngưỡng Tuổi thọ Chức năng (Func50 = 50% cảm biến kết nối Sink)', fontsize=8.3, color='dimgray', fontweight='bold')

    ax.annotate('EC-only: Sập tại R73\nLB-Hard: Kéo dài tới R79 (+6 rounds\nnhờ xoay vòng tải & năng lượng)',
                xy=(79, 50), xytext=(28, 30),
                arrowprops=dict(arrowstyle="->", color=COLOR_LBHARD, lw=1.5),
                bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9", ec=COLOR_LBHARD, lw=1.1),
                fontsize=8.3, fontweight='bold', color='#1b5e20')

    ax.annotate('LB-ECMHR Soft (α=0.20→0.02):\nMở khóa dự phòng khẩn cấp khi vành đai\nchạm 20%, kéo dài kết nối tới Round 96!',
                xy=(96, 50), xytext=(42, 72),
                arrowprops=dict(arrowstyle="->", color=COLOR_LBSOFT, lw=1.6),
                bbox=dict(boxstyle="round,pad=0.35", fc="#ebf5fb", ec=COLOR_LBSOFT, lw=1.2),
                fontsize=8.4, fontweight='bold', color='#154360')

    ax.set_xlim(0, 102)
    ax.set_ylim(-2, 106)
    ax.set_xlabel('Chu kỳ mô phỏng (Round - 1 round = 1 giờ)')
    ax.set_ylabel('Tỷ lệ kết nối mạng đến Sink (%)')
    ax.set_title('Hình 9. So Sánh Kết Nối Vật Lý C_physical(t) và Kết Nối Định Tuyến C_routing(t) Đến Sink', pad=12)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='lower left', framealpha=0.95, fontsize=8.1)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart4_connectivity_ratio.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def plot_chart5_relay_load(data):
    """Hình 10 (Biểu đồ 5): Phân bố tải trên Top 15 Relays và So sánh CV hậu nghiệm trên cùng tập nút"""
    f_min = data['minimum_hop']['forwarding']
    f_ec = data['ec_only']['forwarding']
    f_lb = data['lb_ecmhr']['forwarding']

    sorted_relays = sorted(f_min.items(), key=lambda x: int(x[1]), reverse=True)[:15]
    top_node_ids = [k for k, v in sorted_relays]
    loads_min = [v for k, v in sorted_relays]
    loads_ec = [f_ec.get(k, 0) for k in top_node_ids]
    loads_lb = [f_lb.get(k, 0) for k in top_node_ids]

    labels = [f"N_{nid}" for nid in top_node_ids]
    x = np.arange(len(labels))
    width = 0.28

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.9), gridspec_kw={'width_ratios': [1.55, 1]})

    ax1.bar(x - width, loads_min, width, label='Minimum-Hop (Đỉnh: 7,490 pkts)',
            color=COLOR_MINHOP, edgecolor='black', linewidth=0.8, alpha=0.9)
    ax1.bar(x, loads_ec, width, label='EC-only No LB (Đỉnh: 6,852 pkts)',
            color=COLOR_ECONLY, edgecolor='black', linewidth=0.8, alpha=0.9)
    ax1.bar(x + width, loads_lb, width, label='LB-ECMHR Hard (Đỉnh: 6,586 pkts, -12.1%)',
            color=COLOR_LBHARD, edgecolor='black', linewidth=0.8, alpha=0.9)

    ax1.set_ylabel('Số gói tin chuyển tiếp lũy kế (Packets)')
    ax1.set_xlabel('Mã định danh 15 nút Relay trọng yếu gần Sink')
    ax1.set_title('Phân bố Tải trên Top 15 Nút Relay Then chốt', pad=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha='right')
    ax1.grid(axis='y', linestyle=':', alpha=0.6)
    ax1.legend(loc='upper right', framealpha=0.95, fontsize=8.2)

    # Panel 2: Hệ số biến thiên tải CV hậu nghiệm trên CÙNG TẬP NÚT
    cv_groups = [
        'CV Toàn mạng\n(Cố định N=500 nút)',
        'CV Vành đai 1-Hop\n(Cố định 14 nút)',
        'CV Cửa sổ trượt\n(Trung bình W=24h)'
    ]
    cv_min_vals = [
        data['minimum_hop']['cumulative_relay_load_cv_all'],
        data['minimum_hop']['cumulative_relay_load_cv_1hop'],
        data['minimum_hop']['relay_load_cv_average']
    ]
    cv_ec_vals = [
        data['ec_only']['cumulative_relay_load_cv_all'],
        data['ec_only']['cumulative_relay_load_cv_1hop'],
        data['ec_only']['relay_load_cv_average']
    ]
    cv_lb_vals = [
        data['lb_ecmhr']['cumulative_relay_load_cv_all'],
        data['lb_ecmhr']['cumulative_relay_load_cv_1hop'],
        data['lb_ecmhr']['relay_load_cv_average']
    ]
    cv_soft_vals = [
        data['lb_ecmhr_soft']['cumulative_relay_load_cv_all'],
        data['lb_ecmhr_soft']['cumulative_relay_load_cv_1hop'],
        data['lb_ecmhr_soft']['relay_load_cv_average']
    ]

    xg = np.arange(len(cv_groups))
    wg = 0.19
    ax2.bar(xg - 1.5*wg, cv_min_vals, wg, label='Minimum-Hop', color=COLOR_MINHOP, edgecolor='black', alpha=0.9)
    ax2.bar(xg - 0.5*wg, cv_ec_vals, wg, label='EC-only (No LB)', color=COLOR_ECONLY, edgecolor='black', alpha=0.9)
    ax2.bar(xg + 0.5*wg, cv_lb_vals, wg, label='LB-ECMHR (Hard)', color=COLOR_LBHARD, edgecolor='black', alpha=0.9)
    ax2.bar(xg + 1.5*wg, cv_soft_vals, wg, label='LB-ECMHR (Soft)', color=COLOR_LBSOFT, edgecolor='black', alpha=0.9)

    ax2.set_xticks(xg)
    ax2.set_xticklabels(cv_groups, fontsize=8.4)
    ax2.set_ylim(0, 2.55)
    ax2.set_ylabel('Hệ số biến thiên tải CV (Thấp hơn = Đều hơn)')
    ax2.set_title('So sánh Công bằng Hệ số CV Trên Cùng Tập Nút', pad=10)
    ax2.grid(axis='y', linestyle=':', alpha=0.6)
    ax2.legend(loc='upper center', ncol=2, fontsize=7.9, framealpha=0.95)

    for i in range(len(cv_groups)):
        ax2.text(xg[i] - 1.5*wg, cv_min_vals[i] + 0.04, f"{cv_min_vals[i]:.2f}", ha='center', fontsize=7.5, color=COLOR_MINHOP, fontweight='bold')
        ax2.text(xg[i] + 0.5*wg, cv_lb_vals[i] + 0.04, f"{cv_lb_vals[i]:.2f}", ha='center', fontsize=7.5, color=COLOR_LBHARD, fontweight='bold')
        ax2.text(xg[i] + 1.5*wg, cv_soft_vals[i] + 0.04, f"{cv_soft_vals[i]:.2f}", ha='center', fontsize=7.5, color=COLOR_LBSOFT, fontweight='bold')

    plt.suptitle('Hình 10. Phân Bố Tải Đỉnh Trên Top 15 Relay và Hệ Số Biến Thiên Tải (CV) Trên Cùng Tập Nút', y=1.02, fontsize=12, fontweight='bold')
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart5_relay_load_distribution.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def plot_chart6_delivered_data(data):
    """Hình 11 (Biểu đồ 6): Dữ liệu chuyển giao lũy kế về Sink theo Round (MiB) cho cả 4 mô hình"""
    h_min = data['minimum_hop']['history']
    h_ec = data['ec_only']['history']
    h_lb = data['lb_ecmhr']['history']
    h_soft = data['lb_ecmhr_soft']['history']

    rounds = [0] + [item['round'] for item in h_min]
    d_min = [0.0] + [item.get('delivered_data_mb', 0.0) for item in h_min]
    d_ec = [0.0] + [item.get('delivered_data_mb', 0.0) for item in h_ec]
    d_lb = [0.0] + [item.get('delivered_data_mb', 0.0) for item in h_lb]
    d_soft = [0.0] + [item.get('delivered_data_mb', 0.0) for item in h_soft]

    fig, ax = plt.subplots(figsize=(9.2, 5.0))

    ax.plot(rounds, d_soft, color=COLOR_LBSOFT, linewidth=2.8,
            label=f"LB-ECMHR Soft Fallback (α=0.20→0.02): {d_soft[-1]:.2f} MiB (PDR 95.62%, 0 nút chết)")
    ax.plot(rounds, d_min, color=COLOR_MINHOP, linewidth=2.4, linestyle='--',
            label=f"Minimum-Hop (Baseline): {d_min[-1]:.2f} MiB (PDR 92.27%, Sched 87.78%, 60 nút chết)")
    ax.plot(rounds, d_lb, color=COLOR_LBHARD, linewidth=2.4, linestyle='-.',
            label=f"LB-ECMHR Hard (α=0.20): {d_lb[-1]:.2f} MiB (PDR 79.92%, Bảo lưu cứng 20% pin)")
    ax.plot(rounds, d_ec, color=COLOR_ECONLY, linewidth=2.0, linestyle=':',
            label=f"EC-only (Hard α=0.20, No LB): {d_ec[-1]:.2f} MiB (PDR 74.54%, Sập sớm từ R73)")

    fnd_round = 21
    fnd_data_min = d_min[fnd_round]
    ax.axvline(x=fnd_round, color=COLOR_WARN, linestyle='--', linewidth=1.5, alpha=0.85)
    ax.plot(fnd_round, fnd_data_min, marker='o', markersize=8, color=COLOR_WARN, markeredgecolor='black')

    ax.annotate(f'Mốc FND Minimum-Hop = Round 21\nChỉ thu được {fnd_data_min:.2f} MiB trước khi có nút chết',
                xy=(fnd_round, fnd_data_min), xytext=(fnd_round + 6, fnd_data_min - 0.55),
                arrowprops=dict(arrowstyle="->", color=COLOR_WARN, lw=1.5),
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec=COLOR_WARN, lw=1.1),
                fontweight='bold', fontsize=8.4)

    ax.annotate(f'LB-ECMHR Soft đạt {d_soft[-1]:.2f} MiB (+8.9% so với Min-Hop)\nđồng thời giữ FND > 100 (0 nút chết)!',
                xy=(100, d_soft[-1]), xytext=(45, 5.25),
                arrowprops=dict(arrowstyle="->", color=COLOR_LBSOFT, lw=1.6),
                bbox=dict(boxstyle="round,pad=0.35", fc="#ebf5fb", ec=COLOR_LBSOFT, lw=1.2),
                fontweight='bold', fontsize=8.5, color='#154360')

    ax.set_xlim(0, 105)
    ax.set_ylim(0, 6.4)
    ax.set_xlabel('Chu kỳ mô phỏng (Round - 1 round = 1 giờ)')
    ax.set_ylabel('Tổng dữ liệu chuyển giao về Sink (MiB)')
    ax.set_title('Hình 11. Dữ Liệu Chuyển Giao Lũy Kế Về Sink và Cột Mốc An Toàn FND (Đơn vị: MiB)', pad=12)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper left', framealpha=0.95, fontsize=8.2)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart6_delivered_data.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def plot_hinh4_detour_schematic():
    """Hình 4: Sơ đồ minh họa quá trình chọn đường thay thế của LB-ECMHR khi relay bị quá tải"""
    fig, ax = plt.subplots(figsize=(9.2, 4.6))

    nodes = {
        'S': (0.8, 0, 'Source (S)', '#34495e', 'white'),
        'A': (2.6, 1.2, 'Relay A\n(Load: 0.8)', '#2980b9', 'white'),
        'B': (4.8, 1.2, 'Relay B [QUÁ TẢI]\n(Load: 2.4 ≥ β=2.0)', COLOR_MINHOP, 'white'),
        'C': (2.4, -1.2, 'Relay C\n(Load: 0.7)', '#27ae60', 'white'),
        'D': (4.1, -1.2, 'Relay D\n(Load: 0.9)', '#27ae60', 'white'),
        'E': (5.7, -1.2, 'Relay E\n(Load: 1.1)', '#27ae60', 'white'),
        'Sink': (7.5, 0, 'SINK\n(Đích đến)', '#8e44ad', 'white')
    }

    edges_p1 = [('S', 'A'), ('A', 'B'), ('B', 'Sink')]
    for u, v in edges_p1:
        x1, y1 = nodes[u][0], nodes[u][1]
        x2, y2 = nodes[v][0], nodes[v][1]
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=COLOR_MINHOP, lw=2.2, linestyle='--',
                                    mutation_scale=18))

    edges_p2 = [('S', 'C'), ('C', 'D'), ('D', 'E'), ('E', 'Sink')]
    for u, v in edges_p2:
        x1, y1 = nodes[u][0], nodes[u][1]
        x2, y2 = nodes[v][0], nodes[v][1]
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=COLOR_LBHARD, lw=2.5,
                                    mutation_scale=18))

    for name, (nx_c, ny_c, label, bg, fg) in nodes.items():
        box_w, box_h = (1.5, 0.75) if 'Sink' not in name and 'B' not in name else (1.8, 0.85)
        rect = patches.FancyBboxPatch((nx_c - box_w/2, ny_c - box_h/2), box_w, box_h,
                                     boxstyle="round,pad=0.1,rounding_size=0.15",
                                     ec="black", fc=bg, lw=1.5, zorder=4)
        ax.add_patch(rect)
        ax.text(nx_c, ny_c, label, ha='center', va='center', color=fg, fontweight='bold', fontsize=8.5, zorder=5)

    ax.text(3.7, 1.9, 'Đường P1: 3 hops (Ngắn nhất) ──► BỊ NÉ TRÁNH do Relay B quá tải (Load = 2.4)',
            ha='center', va='center', color=COLOR_MINHOP, fontweight='bold', fontsize=9.5,
            bbox=dict(boxstyle="square,pad=0.3", fc="#ffebee", ec=COLOR_MINHOP, lw=1))

    ax.text(4.0, -2.0, 'Đường P2: 4 hops (H_detour = 4 ≤ 3 + 1) ──► ĐƯỢC CHỌN nhờ thỏa Bounded Detour',
            ha='center', va='center', color=COLOR_LBHARD, fontweight='bold', fontsize=9.5,
            bbox=dict(boxstyle="square,pad=0.3", fc="#e8f5e9", ec=COLOR_LBHARD, lw=1))

    ax.set_xlim(-0.2, 8.8)
    ax.set_ylim(-2.5, 2.5)
    ax.axis('off')
    ax.set_title('Hình 4. Minh Họa Cơ Chế Chọn Tuyến Đường Vòng Thay Thế Khi Relay Bị Quá Tải',
                 fontsize=12, fontweight='bold', pad=15)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "hinh4_lb_ecmhr_detour_example.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def main():
    print("=== Đang nạp dữ liệu thực nghiệm đã chuẩn hóa ===")
    data = load_simulation_data()

    print("=== Đang vẽ 6 biểu đồ kết quả thực nghiệm và sơ đồ Hình 4 ===")
    plot_chart1_fnd_comparison(data)
    plot_chart2_alive_nodes(data)
    plot_chart3_energy(data)
    plot_chart4_connectivity(data)
    plot_chart5_relay_load(data)
    plot_chart6_delivered_data(data)
    plot_hinh4_detour_schematic()
    print("=== HOÀN TẤT XUẤT ẢNH BIỂU ĐỒ KỊCH BẢN A ===")


if __name__ == "__main__":
    main()
