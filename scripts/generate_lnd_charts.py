"""
Script: generate_lnd_charts.py
Mô tả: Vẽ bộ 3 biểu đồ vòng đời toàn diện cho tới khi đạt LND (Last Node Death - 100% nút chết)
trong Kịch bản B (1000 rounds, có E_basal = 0.002 J/round) cho Minimum-Hop, LB-ECMHR Hard (α=0.20)
và LB-ECMHR Soft Fallback (α=0.20→0.02) theo chuẩn xuất bản khoa học (PNG 300 DPI).
"""

import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt

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
plt.rcParams['legend.fontsize'] = 8.4
plt.rcParams['figure.titlesize'] = 12.5

COLOR_MINHOP = '#d9534f'   # Đỏ cam coral - Minimum-Hop
COLOR_LBHARD = '#1b7837'   # Xanh lục bảo đậm - LB-ECMHR Hard
COLOR_LBSOFT = '#1f78b4'   # Xanh dương đậm - LB-ECMHR Soft
COLOR_WARN = '#e67e22'

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "docs", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)
LND_DATA_FILE = os.path.join(ROOT_DIR, "outputs", "compare_routing_lnd.json")


def load_lnd_data():
    if not os.path.exists(LND_DATA_FILE):
        raise FileNotFoundError(f"Chưa tìm thấy file dữ liệu LND: {LND_DATA_FILE}")
    with open(LND_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_chart7_lnd_milestones(data):
    """Hình 12 (Biểu đồ 7): So sánh trọn vẹn các cột mốc FND, Func50, HND, LND và lượng dữ liệu thu thập"""
    m_min = data["minimum_hop"]
    m_lb = data["lb_ecmhr"]
    m_soft = data["lb_ecmhr_soft"]

    milestones = [
        'FND\n(1 nút chết)',
        'Func50\n(Còn ≥50% kết nối)',
        'HND\n(250 nút chết)',
        'LND\n(500 nút chết)'
    ]
    min_rounds = [m_min['fnd_round'], m_min['functional_50_round'], m_min['hnd_round'], m_min['lnd_round']]
    lb_rounds = [m_lb['fnd_round'], m_lb['functional_50_round'], m_lb['hnd_round'], m_lb['lnd_round']]
    soft_rounds = [m_soft['fnd_round'], m_soft['functional_50_round'], m_soft['hnd_round'], m_soft['lnd_round']]

    x = np.arange(len(milestones))
    width = 0.26

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.9), gridspec_kw={'width_ratios': [1.25, 1]})

    b1 = ax1.bar(x - width, min_rounds, width, label='Minimum-Hop (Baseline)', color=COLOR_MINHOP, edgecolor='black', alpha=0.9)
    b2 = ax1.bar(x, lb_rounds, width, label='LB-ECMHR Hard (α=0.20)', color=COLOR_LBHARD, edgecolor='black', alpha=0.9)
    b3 = ax1.bar(x + width, soft_rounds, width, label='LB-ECMHR Soft (α=0.20→0.02)', color=COLOR_LBSOFT, edgecolor='black', alpha=0.9)

    ax1.set_ylabel('Thời điểm xuất hiện cột mốc (Round)')
    ax1.set_title('So sánh Thời điểm Đạt FND, Func50, HND và LND', pad=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(milestones, fontsize=8.6)
    ax1.set_ylim(0, 1180)
    ax1.grid(axis='y', linestyle=':', alpha=0.6)
    ax1.legend(loc='upper left', framealpha=0.95)

    for bars, col in [(b1, COLOR_MINHOP), (b2, COLOR_LBHARD), (b3, COLOR_LBSOFT)]:
        for bar in bars:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2.0, h + 15, f"R{int(h)}", ha='center', va='bottom',
                     fontweight='bold', color=col, fontsize=8.0)

    ax1.annotate(f"FND kéo dài 4.3×–6.0×:\nMin-Hop R{m_min['fnd_round']} → Soft R{m_soft['fnd_round']} / Hard R{m_lb['fnd_round']}",
                 xy=(0, m_lb['fnd_round']), xytext=(0.05, 360),
                 arrowprops=dict(arrowstyle="->", color=COLOR_LBHARD, lw=1.5),
                 bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9", ec=COLOR_LBHARD, lw=1.1),
                 fontsize=8.3, fontweight='bold', color='#1b5e20')

    # Panel 2: Lượng dữ liệu chuyển giao (MiB) tại FND và LND
    d_labels = ['Dữ liệu tại FND\n(100% nút còn sống)', 'Tổng Dữ liệu tại LND\n(Trọn vòng đời 1000 R)']
    xd = np.arange(len(d_labels))
    min_d = [m_min['delivered_data_at_fnd_mib'], m_min['delivered_data_at_lnd_mib']]
    lb_d = [m_lb['delivered_data_at_fnd_mib'], m_lb['delivered_data_at_lnd_mib']]
    soft_d = [m_soft['delivered_data_at_fnd_mib'], m_soft['delivered_data_at_lnd_mib']]

    d1 = ax2.bar(xd - width, min_d, width, label='Minimum-Hop (MiB)', color=COLOR_MINHOP, edgecolor='black', alpha=0.9)
    d2 = ax2.bar(xd, lb_d, width, label='LB-ECMHR Hard (MiB)', color=COLOR_LBHARD, edgecolor='black', alpha=0.9)
    d3 = ax2.bar(xd + width, soft_d, width, label='LB-ECMHR Soft (MiB)', color=COLOR_LBSOFT, edgecolor='black', alpha=0.9)

    ax2.set_ylabel('Tổng dữ liệu chuyển giao lũy kế (MiB)')
    ax2.set_title('Dữ liệu Thu thập tại Mốc FND và Trọn Vòng Đời LND', pad=10)
    ax2.set_xticks(xd)
    ax2.set_xticklabels(d_labels)
    ax2.set_ylim(0, 6.8)
    ax2.grid(axis='y', linestyle=':', alpha=0.6)
    ax2.legend(loc='upper left', framealpha=0.95)

    for bars, col in [(d1, COLOR_MINHOP), (d2, COLOR_LBHARD), (d3, COLOR_LBSOFT)]:
        for bar in bars:
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2.0, h + 0.10, f"{h:.2f}", ha='center', va='bottom',
                     fontweight='bold', color=col, fontsize=8.4)

    ax2.annotate(f"LB-ECMHR Soft dẫn đầu cả 2 mốc:\n• Tại FND: {m_soft['delivered_data_at_fnd_mib']:.2f} MiB (gấp 4.25× Min-Hop)\n• Tại LND: {m_soft['delivered_data_at_lnd_mib']:.2f} MiB (vượt Min-Hop!)",
                 xy=(1 + width, m_soft['delivered_data_at_lnd_mib']), xytext=(0.15, 5.55),
                 arrowprops=dict(arrowstyle="->", color=COLOR_LBSOFT, lw=1.5),
                 bbox=dict(boxstyle="round,pad=0.3", fc="#ebf5fb", ec=COLOR_LBSOFT, lw=1.1),
                 fontsize=8.1, fontweight='bold', color='#154360')

    plt.suptitle('Hình 12. So Sánh Cột Mốc Vòng Đời (FND, Func50, HND, LND) và Dữ Liệu Thu Thập (Kịch Bản B)', y=1.02, fontsize=12, fontweight='bold')
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart7_lnd_milestones.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def plot_chart8_lnd_alive_dead(data):
    """Hình 13 (Biểu đồ 8): Đường cong suy giảm số nút sống (Alive Nodes) và tăng số nút chết (Dead Nodes) tới LND"""
    m_min = data["minimum_hop"]
    m_lb = data["lb_ecmhr"]
    m_soft = data["lb_ecmhr_soft"]

    h_min = m_min["history"]
    h_lb = m_lb["history"]
    h_soft = m_soft["history"]

    r_min = [0] + [item["round"] for item in h_min]
    alive_min = [500] + [item["alive_nodes"] for item in h_min]
    dead_min = [0] + [item["dead_nodes"] for item in h_min]

    r_lb = [0] + [item["round"] for item in h_lb]
    alive_lb = [500] + [item["alive_nodes"] for item in h_lb]
    dead_lb = [0] + [item["dead_nodes"] for item in h_lb]

    r_soft = [0] + [item["round"] for item in h_soft]
    alive_soft = [500] + [item["alive_nodes"] for item in h_soft]
    dead_soft = [0] + [item["dead_nodes"] for item in h_soft]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.9))

    ax1.step(r_lb, alive_lb, where='post', color=COLOR_LBHARD, linewidth=2.5,
             label=f"LB-ECMHR Hard (FND=R{m_lb['fnd_round']}, HND=R{m_lb['hnd_round']}, LND=R{m_lb['lnd_round']})")
    ax1.step(r_soft, alive_soft, where='post', color=COLOR_LBSOFT, linewidth=2.2, linestyle='-.',
             label=f"LB-ECMHR Soft (FND=R{m_soft['fnd_round']}, HND=R{m_soft['hnd_round']}, LND=R{m_soft['lnd_round']})")
    ax1.step(r_min, alive_min, where='post', color=COLOR_MINHOP, linewidth=2.2, linestyle='--',
             label=f"Minimum-Hop (FND=R{m_min['fnd_round']}, HND=R{m_min['hnd_round']}, LND=R{m_min['lnd_round']})")

    ax1.axhline(y=250, color='gray', linestyle=':', linewidth=1.2, alpha=0.8)
    ax1.text(30, 260, 'Ngưỡng HND (50% = 250 nút sống)', fontsize=8.4, color='dimgray', fontweight='bold')

    ax1.plot(m_min['fnd_round'], 499, 'o', color=COLOR_MINHOP, markersize=7, markeredgecolor='black')
    ax1.plot(m_soft['fnd_round'], 499, '^', color=COLOR_LBSOFT, markersize=7, markeredgecolor='black')
    ax1.plot(m_lb['fnd_round'], 499, 's', color=COLOR_LBHARD, markersize=7, markeredgecolor='black')

    ax1.annotate(f"FND Min-Hop (R{m_min['fnd_round']})", xy=(m_min['fnd_round'], 499), xytext=(45, 420),
                 arrowprops=dict(arrowstyle="->", color=COLOR_MINHOP, lw=1.4),
                 fontsize=8.2, fontweight='bold', color=COLOR_MINHOP,
                 bbox=dict(boxstyle="round,pad=0.25", fc="#ffebee", ec=COLOR_MINHOP))

    ax1.annotate(f"FND Soft (R{m_soft['fnd_round']}) & Hard (R{m_lb['fnd_round']})",
                 xy=(m_lb['fnd_round'], 499), xytext=(220, 468),
                 arrowprops=dict(arrowstyle="->", color=COLOR_LBHARD, lw=1.4),
                 fontsize=8.2, fontweight='bold', color='#1b5e20',
                 bbox=dict(boxstyle="round,pad=0.25", fc="#e8f5e9", ec=COLOR_LBHARD))

    ax1.set_xlim(0, 1050)
    ax1.set_ylim(-15, 535)
    ax1.set_xlabel('Chu kỳ mô phỏng (Round)')
    ax1.set_ylabel('Số lượng nút cảm biến còn sống (Alive Nodes)')
    ax1.set_title('Đường cong Sống sót (Alive Nodes) tới khi đạt LND', pad=10)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='lower left', framealpha=0.95, fontsize=8.1)

    # Panel 2: Dead nodes vs Round
    ax2.step(r_lb, dead_lb, where='post', color=COLOR_LBHARD, linewidth=2.4, label='LB-ECMHR Hard - Dead Nodes')
    ax2.step(r_soft, dead_soft, where='post', color=COLOR_LBSOFT, linewidth=2.2, linestyle='-.', label='LB-ECMHR Soft - Dead Nodes')
    ax2.step(r_min, dead_min, where='post', color=COLOR_MINHOP, linewidth=2.2, linestyle='--', label='Minimum-Hop - Dead Nodes')

    ax2.annotate('Sau khi vành đai relay cạn năng lượng (R88),\ncác nút xa Sink bị cô lập và tiêu hao năng lượng nền\n(E_basal = 0.002 J/round) cho tới khi đạt LND (~R995)',
                 xy=(500, 95), xytext=(110, 235),
                 arrowprops=dict(arrowstyle="->", color='darkslategray', lw=1.4),
                 bbox=dict(boxstyle="round,pad=0.35", fc="#f8f9f9", ec="gray", lw=1),
                 fontsize=8.1, fontweight='bold')

    ax2.set_xlim(0, 1050)
    ax2.set_ylim(-15, 535)
    ax2.set_xlabel('Chu kỳ mô phỏng (Round)')
    ax2.set_ylabel('Số lượng nút chết lũy kế (Dead Nodes)')
    ax2.set_title('Đường cong Nút Chết (Dead Nodes) tới LND (500/500 nút)', pad=10)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='upper left', framealpha=0.95, fontsize=8.2)

    plt.suptitle('Hình 13. Diễn Biến Số Nút Sống (Alive) và Nút Chết (Dead) Trên Toàn Bộ Vòng Đời Tới LND', y=1.02, fontsize=12, fontweight='bold')
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart8_lnd_alive_dead_curves.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def plot_chart9_lnd_energy_connectivity(data):
    """Hình 14 (Biểu đồ 9): Suy giảm Năng lượng còn lại (tới 0 J) và Phân rã Năng lượng Radio vs Basal"""
    m_min = data["minimum_hop"]
    m_lb = data["lb_ecmhr"]
    m_soft = data["lb_ecmhr_soft"]

    h_min = m_min["history"]
    h_lb = m_lb["history"]
    h_soft = m_soft["history"]

    r_min = [0] + [item["round"] for item in h_min]
    erem_min = [1000.0] + [item["total_remaining_energy_j"] for item in h_min]

    r_lb = [0] + [item["round"] for item in h_lb]
    erem_lb = [1000.0] + [item["total_remaining_energy_j"] for item in h_lb]

    r_soft = [0] + [item["round"] for item in h_soft]
    erem_soft = [1000.0] + [item["total_remaining_energy_j"] for item in h_soft]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.9), gridspec_kw={'width_ratios': [1.22, 1]})

    ax1.plot(r_lb, erem_lb, color=COLOR_LBHARD, linewidth=2.5, label=f"LB-ECMHR Hard (LND = R{m_lb['lnd_round']})")
    ax1.plot(r_soft, erem_soft, color=COLOR_LBSOFT, linewidth=2.3, linestyle='-.', label=f"LB-ECMHR Soft (LND = R{m_soft['lnd_round']})")
    ax1.plot(r_min, erem_min, color=COLOR_MINHOP, linewidth=2.2, linestyle='--', label=f"Minimum-Hop (LND = R{m_min['lnd_round']})")

    ax1.annotate('Giai đoạn 1 (R1–R88):\nTiêu hao năng lượng Radio đa chặng\nkết hợp năng lượng nền E_basal',
                 xy=(50, 810), xytext=(25, 230),
                 arrowprops=dict(arrowstyle="->", color='black', lw=1.4),
                 bbox=dict(boxstyle="round,pad=0.3", fc="#fff9c4", ec="#fbc02d"),
                 fontsize=8.2, fontweight='bold')

    ax1.annotate('Giai đoạn 2 (R89–LND):\nTiêu hao năng lượng nền E_basal\ncho tới khi toàn mạng về 0 J',
                 xy=(500, 390), xytext=(390, 630),
                 arrowprops=dict(arrowstyle="->", color=COLOR_LBHARD, lw=1.4),
                 bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9", ec=COLOR_LBHARD),
                 fontsize=8.2, fontweight='bold', color='#1b5e20')

    ax1.set_xlim(0, 1050)
    ax1.set_ylim(-20, 1060)
    ax1.set_xlabel('Chu kỳ mô phỏng (Round)')
    ax1.set_ylabel('Tổng năng lượng còn lại toàn mạng (Joules)')
    ax1.set_title('Suy giảm Năng lượng Toàn mạng từ 1000 J về 0 J (LND)', pad=10)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='upper right', framealpha=0.95)

    # Panel 2: Stacked bar phân tách Radio Energy vs Basal Energy trong tổng 1000 J
    models = ['Minimum-Hop', 'EC-only\n(No LB)', 'LB-ECMHR\n(Hard)', 'LB-ECMHR\n(Soft)']
    m_ec = data["ec_only"]
    radio_e = [m_min['radio_energy_consumed_j'], m_ec['radio_energy_consumed_j'], m_lb['radio_energy_consumed_j'], m_soft['radio_energy_consumed_j']]
    basal_e = [m_min['basal_energy_consumed_j'], m_ec['basal_energy_consumed_j'], m_lb['basal_energy_consumed_j'], m_soft['basal_energy_consumed_j']]
    radio_eff = [m_min['radio_efficiency_bits_per_j']/1000, m_ec['radio_efficiency_bits_per_j']/1000, m_lb['radio_efficiency_bits_per_j']/1000, m_soft['radio_efficiency_bits_per_j']/1000]

    xm = np.arange(len(models))
    ax2.bar(xm, radio_e, width=0.48, color='#2980b9', edgecolor='black', label='Năng lượng Truyền nhận Radio (E_radio)')
    ax2.bar(xm, basal_e, width=0.48, bottom=radio_e, color='#bdc3c7', edgecolor='black', hatch='//', label='Năng lượng Nền Duy trì (E_basal)')

    for i, (re, be, reff) in enumerate(zip(radio_e, basal_e, radio_eff)):
        ax2.text(i, re/2, f"Radio:\n{re:.1f} J\n({reff:.1f} kb/J)", ha='center', va='center', color='white', fontweight='bold', fontsize=8.0)
        ax2.text(i, re + be/2, f"Basal:\n{be:.1f} J", ha='center', va='center', color='#2c3e50', fontweight='bold', fontsize=8.2)

    ax2.set_xticks(xm)
    ax2.set_xticklabels(models)
    ax2.set_ylim(0, 1180)
    ax2.set_ylabel('Phân rã Tổng năng lượng tiêu thụ (Joules)')
    ax2.set_title('Tách bạch Năng lượng Radio và Năng lượng Nền tại LND', pad=10)
    ax2.grid(axis='y', linestyle=':', alpha=0.6)
    ax2.legend(loc='upper right', framealpha=0.95, fontsize=8.2)

    plt.suptitle('Hình 14. Suy Giảm Năng Lượng Toàn Mạng (1000 J → 0 J) và Phân Rã Năng Lượng Radio / Nền Tới LND', y=1.02, fontsize=12, fontweight='bold')
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "chart9_lnd_energy_and_connectivity.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Đã lưu: {out_path}")


def main():
    print("=== Đang nạp dữ liệu vòng đời LND ===")
    data = load_lnd_data()

    print("=== Đang vẽ 3 biểu đồ vòng đời LND (Hình 12, 13, 14) ===")
    plot_chart7_lnd_milestones(data)
    plot_chart8_lnd_alive_dead(data)
    plot_chart9_lnd_energy_connectivity(data)
    print("=== HOÀN TẤT XUẤT 3 BIỂU ĐỒ LND ===")


if __name__ == "__main__":
    main()
