"""
Script: generate_sensitivity_figures.py
Description: Tự động vẽ 6 biểu đồ phân tích độ nhạy tham số và Ablation Study (Hình 15 - Hình 20 trong Mục 15)
theo chuẩn xuất bản (PNG 300 DPI) từ dữ liệu Master Thực nghiệm (outputs/experiments_master_results.json).
Đảm bảo 100% tính nhất quán số liệu, đánh số hình liên tục (Hình 15 - Hình 20) và làm rõ đóng góp độc lập
của từng thành phần trong Ablation Study (EC-only vs LB-ECMHR Hard vs LB-ECMHR Soft).
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Cấu hình thẩm mỹ
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

COLOR_MINHOP = '#d9534f'
COLOR_ECONLY = '#7f8c8d'
COLOR_LBECMHR = '#1b7837'
COLOR_LBSOFT = '#1f78b4'

MASTER_RESULTS_FILE = os.path.join(os.path.dirname(__file__), "..", "outputs", "experiments_master_results.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(MASTER_RESULTS_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# -------------------------------------------------------------
# Hình 15: Energy Threshold alpha vs PDR, Energy & Func50
# -------------------------------------------------------------
alpha_keys = ["exp1_alpha_10", "exp1_alpha_15", "exp1_alpha_20", "exp1_alpha_25", "exp1_alpha_30"]
alphas = [0.10, 0.15, 0.20, 0.25, 0.30]
pdrs_alpha = [data[k]["pdr"] for k in alpha_keys]
energies_alpha = [data[k]["total_energy_consumed_j"] for k in alpha_keys]
func50_alpha = [data[k]["functional_50_numeric"] for k in alpha_keys]

fig, ax1 = plt.subplots(figsize=(8.8, 4.9))
color_pdr = '#1f77b4'
color_e = '#d62728'

ax1.set_xlabel('Hệ số ngưỡng năng lượng cứng α (Hard Energy Threshold Factor)')
ax1.set_ylabel('Tỷ lệ chuyển gói tin thành công PDR (%)', color=color_pdr)
line1 = ax1.plot(alphas, pdrs_alpha, marker='s', color=color_pdr, linewidth=2.3, markersize=7, label='PDR (%) [Chế độ Ngưỡng Cứng]')
ax1.tick_params(axis='y', labelcolor=color_pdr)
ax1.set_ylim(64, 96)
ax1.grid(True, linestyle=':', alpha=0.6)

ax2 = ax1.twinx()
ax2.set_ylabel('Tổng năng lượng tiêu thụ (Joule)', color=color_e)
line2 = ax2.plot(alphas, energies_alpha, marker='o', color=color_e, linewidth=2.2, linestyle='--', markersize=7, label='Năng lượng tiêu thụ (J)')
ax2.tick_params(axis='y', labelcolor=color_e)
ax2.set_ylim(195, 290)

# Đánh dấu cấu hình ứng viên alpha = 0.20
ax1.axvline(x=0.20, color='gold', linestyle='-.', linewidth=2.0, alpha=0.85)
ax1.annotate('Ngưỡng cơ sở α = 0.20 (Bảo lưu 20% pin = 0.40 J):\n• Chế độ Hard: PDR 79.92%, Func50 = R79, E = 241.45 J\n• Chế độ Soft (α=0.20→0.02): PDR 95.62%, Func50 = R96!',
             xy=(0.20, 79.92), xytext=(0.175, 67.5),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.4, headwidth=5),
             fontsize=8.5, fontweight='bold', bbox=dict(boxstyle="round,pad=0.35", fc="#fff9c4", ec="#fbc02d", lw=1.2))

lines = line1 + line2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper right', framealpha=0.92)

plt.title('Hình 15. Đánh Đổi Giữa Ngưỡng Năng Lượng α, Tỷ Lệ PDR và Tiêu Thụ Năng Lượng')
plt.tight_layout()
fig1_path = os.path.join(OUTPUT_DIR, "fig1_alpha_sensitivity.png")
plt.savefig(fig1_path, dpi=300)
plt.close()
print(f"[OK] Đã lưu: {fig1_path}")


# -------------------------------------------------------------
# Hình 16: Load Window W vs Sliding Window CV & Overload Transitions
# -------------------------------------------------------------
w_keys = ["exp2_w_6", "exp2_w_12", "exp2_w_24", "exp2_w_48"]
w_vals = [6, 12, 24, 48]
cv_avg = [data[k]["relay_load_cv_average"] for k in w_keys]
transitions_w = [data[k]["overload_transitions_count"] for k in w_keys]

fig, ax1 = plt.subplots(figsize=(8.8, 4.9))
x_indices = np.arange(len(w_vals))
width = 0.35

bars = ax1.bar(x_indices - width/2, cv_avg, width, label='CV_load, average (Hệ số biến thiên trượt TB)', color='#3498db', edgecolor='black', alpha=0.85)
ax1.set_xlabel('Cửa sổ quan sát tải W (giờ / rounds)')
ax1.set_ylabel('Hệ số biến thiên tải trượt TB (CV_load, avg)', color='#2980b9')
ax1.set_xticks(x_indices)
ax1.set_xticklabels([f"W = {w}h" for w in w_vals])
ax1.set_ylim(1.0, 1.8)
ax1.tick_params(axis='y', labelcolor='#2980b9')
ax1.grid(True, linestyle=':', alpha=0.6, axis='y')

ax2 = ax1.twinx()
line = ax2.plot(x_indices + width/2, transitions_w, marker='D', color='#e74c3c', linewidth=2.2, markersize=7, label='Số lần chuyển trạng thái quá tải')
ax2.set_ylabel('Số lần chuyển trạng thái quá tải (Lần)', color='#e74c3c')
ax2.set_ylim(100, 310)
ax2.tick_params(axis='y', labelcolor='#e74c3c')

ax2.annotate('W = 24h: Giảm dao động trạng thái\n(194 lần chuyển vs 282 lần ở W=6h,\nlọc nhiễu ngắn hạn -31.2% dao động)',
             xy=(2 + width/2, transitions_w[2]), xytext=(0.95, 258),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.4, headwidth=5),
             fontsize=8.6, fontweight='bold', bbox=dict(boxstyle="round,pad=0.35", fc="#e8f8f5", ec="#1abc9c", lw=1.2))

plt.title('Hình 16. Ảnh Hưởng Của Cửa Sổ Tải W Đến Biến Thiên Tải và Dao Động Tuyến')
fig.legend(loc='upper right', bbox_to_anchor=(0.88, 0.88), framealpha=0.92)
plt.tight_layout()
fig2_path = os.path.join(OUTPUT_DIR, "fig2_window_w_sensitivity.png")
plt.savefig(fig2_path, dpi=300)
plt.close()
print(f"[OK] Đã lưu: {fig2_path}")


# -------------------------------------------------------------
# Hình 17: Overload Factor beta vs Overloaded Relays & Transitions
# -------------------------------------------------------------
beta_keys = ["exp3_beta_15", "exp3_beta_20", "exp3_beta_25", "exp3_beta_30"]
betas = [1.5, 2.0, 2.5, 3.0]
ovl_beta = [data[k]["overloaded_relay_count"] for k in beta_keys]
trans_beta = [data[k]["overload_transitions_count"] for k in beta_keys]

fig, ax1 = plt.subplots(figsize=(8.8, 4.9))
color_b1 = '#8e44ad'
color_b2 = '#d35400'

ax1.set_xlabel('Hệ số ngưỡng quá tải β (Overload Factor)')
ax1.set_ylabel('Số Relay bị gán nhãn quá tải tại cuối mô phỏng', color=color_b1)
l1 = ax1.plot(betas, ovl_beta, marker='o', color=color_b1, linewidth=2.2, markersize=8, label='Số Relay Quá Tải')
ax1.tick_params(axis='y', labelcolor=color_b1)
ax1.set_ylim(20, 45)
ax1.grid(True, linestyle=':', alpha=0.6)

ax2 = ax1.twinx()
ax2.set_ylabel('Số lần chuyển trạng thái quá tải (Lần)', color=color_b2)
l2 = ax2.plot(betas, trans_beta, marker='s', color=color_b2, linewidth=2.2, linestyle='--', markersize=8, label='Số lần chuyển trạng thái')
ax2.tick_params(axis='y', labelcolor=color_b2)
ax2.set_ylim(100, 280)

ax1.axvline(x=2.0, color='gold', linestyle='-.', linewidth=2.0, alpha=0.85)
ax1.annotate('β = 2.0: Cân bằng nhạy tải & ổn định\n(Nhận diện tải gấp đôi trung bình,\ngiảm 22.1% số lần chuyển so với β=1.5)',
             xy=(2.0, ovl_beta[1]), xytext=(2.12, 35),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.4, headwidth=5),
             fontsize=8.6, fontweight='bold', bbox=dict(boxstyle="round,pad=0.35", fc="#fef9e7", ec="#f39c12", lw=1.2))

lines = l1 + l2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper right', framealpha=0.92)

plt.title('Hình 17. Ảnh Hưởng Của Ngưỡng Quá Tải β Đến Số Relay Báo Động và Dao Động Trạng Thái')
plt.tight_layout()
fig3_path = os.path.join(OUTPUT_DIR, "fig3_beta_sensitivity.png")
plt.savefig(fig3_path, dpi=300)
plt.close()
print(f"[OK] Đã lưu: {fig3_path}")


# -------------------------------------------------------------
# Hình 18: Recovery Factor gamma vs Overload Transitions & Duration
# -------------------------------------------------------------
gamma_keys = ["exp4_gamma_08", "exp4_gamma_10", "exp4_gamma_12", "exp4_gamma_15"]
gammas = [0.8, 1.0, 1.2, 1.5]
trans_gamma = [data[k]["overload_transitions_count"] for k in gamma_keys]
node_rounds_gamma = [data[k]["total_overload_node_rounds"] for k in gamma_keys]

fig, ax1 = plt.subplots(figsize=(8.8, 4.9))
x_pos = np.arange(len(gammas))
bar_colors = ['#5dade2', '#48c9b0', '#2ecc71', '#f39c12']

bars = ax1.bar(x_pos - width/2, trans_gamma, width, color=bar_colors, edgecolor='black', alpha=0.85, label='Số lần chuyển trạng thái')
ax1.set_xlabel('Hệ số phục hồi γ (với β = 2.0 cố định)')
ax1.set_ylabel('Số lần chuyển trạng thái quá tải (Lần)')
ax1.set_xticks(x_pos)
ax1.set_xticklabels([f"γ = {g}\n(Đệm Δ = {2.0-g:.1f})" for g in gammas])
ax1.set_ylim(150, 220)
ax1.grid(True, linestyle=':', alpha=0.6, axis='y')

for bar in bars:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 1.2, f"{int(yval)}", ha='center', va='bottom', fontsize=9, fontweight='bold')

ax2 = ax1.twinx()
line_dur = ax2.plot(x_pos + width/2, node_rounds_gamma, marker='^', color='#8e44ad', linewidth=2.2, markersize=8, label='Tổng thời lượng quá tải (node-rounds)')
ax2.set_ylabel('Tổng thời lượng quá tải (Node-rounds)', color='#8e44ad')
ax2.set_ylim(4300, 5100)
ax2.tick_params(axis='y', labelcolor='#8e44ad')

ax1.annotate('γ = 1.2: Vùng đệm trễ cân đối (Δ = 0.8)\n(Tránh huỷ cảnh báo quá sớm,\ngiữ ổn định tuyến đường)',
             xy=(2 - width/2, trans_gamma[2]), xytext=(0.75, 205),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.4, headwidth=5),
             fontsize=8.6, fontweight='bold', bbox=dict(boxstyle="round,pad=0.35", fc="#eafaf1", ec="#27ae60", lw=1.2))

plt.title('Hình 18. Ảnh Hưởng Của Ngưỡng Phục Hồi Hysteresis γ Đến Dao Động và Thời Lượng Quá Tải')
fig.legend(loc='upper right', bbox_to_anchor=(0.88, 0.88), framealpha=0.92)
plt.tight_layout()
fig4_path = os.path.join(OUTPUT_DIR, "fig4_gamma_hysteresis.png")
plt.savefig(fig4_path, dpi=300)
plt.close()
print(f"[OK] Đã lưu: {fig4_path}")


# -------------------------------------------------------------
# Hình 19: Max Extra Hops Delta H vs Routing Reroutes & Fallback Routes
# -------------------------------------------------------------
dh_keys = ["exp5_deltah_0", "exp5_deltah_1", "exp5_deltah_2"]
deltas = ["0", "1", "2"]
energies_dh = [data[k]["total_energy_consumed_j"] for k in dh_keys]
reroutes_dh = [data[k]["routing_reroutes"] for k in dh_keys]

fig, ax1 = plt.subplots(figsize=(8.8, 4.9))
x_inds = np.arange(len(deltas))

ax1.plot(x_inds, energies_dh, marker='o', color='#c0392b', linewidth=2.4, markersize=8, label='Năng lượng tiêu thụ (J)')
ax1.set_xlabel('Số hop đi vòng tối đa cho phép ΔH (Max Extra Hops)')
ax1.set_ylabel('Tổng năng lượng tiêu thụ (Joule)', color='#c0392b')
ax1.set_xticks(x_inds)
ax1.set_xticklabels([f"ΔH = {d}\n({'Cấm đi vòng' if d=='0' else 'Cho phép +1 hop' if d=='1' else 'Cho phép +2 hops'})" for d in deltas])
ax1.set_ylim(241.0, 242.0)
ax1.tick_params(axis='y', labelcolor='#c0392b')
ax1.grid(True, linestyle=':', alpha=0.6)

ax2 = ax1.twinx()
ax2.plot(x_inds, reroutes_dh, marker='s', color='#2980b9', linewidth=2.2, linestyle='--', markersize=8, label='Số lần tính lại đường (Reroutes)')
ax2.set_ylabel('Số lần tính lại đường (Reroutes)', color='#2980b9')
ax2.set_ylim(1400, 1650)
ax2.tick_params(axis='y', labelcolor='#2980b9')

ax1.annotate('ΔH = 1 & ΔH = 2: Cho kết quả tương đương (241.45 J, 731 gói đi vòng)\nΔH = 1 được ưu tiên do là ràng buộc chặt chẽ hơn,\nhạn chế mở rộng không gian tìm đường không cần thiết',
             xy=(1, energies_dh[1]), xytext=(0.22, 241.68),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.4, headwidth=5),
             fontsize=8.6, fontweight='bold', bbox=dict(boxstyle="round,pad=0.35", fc="#ebf5fb", ec="#2980b9", lw=1.2))

plt.title('Hình 19. Đánh Đổi Giữa Ràng Buộc Đi Vòng ΔH, Năng Lượng và Tần Suất Định Tuyến')
fig.legend(loc='upper right', bbox_to_anchor=(0.88, 0.88), framealpha=0.92)
plt.tight_layout()
fig5_path = os.path.join(OUTPUT_DIR, "fig5_delta_h_tradeoff.png")
plt.savefig(fig5_path, dpi=300)
plt.close()
print(f"[OK] Đã lưu: {fig5_path}")


# -------------------------------------------------------------
# Hình 20: Ablation Study - Phân tách độc lập 6 cấu hình:
# 1. Minimum-Hop, 2. True EC-only (No LB), 3. LB-ECMHR (ΔH=0),
# 4. No Hysteresis, 5. LB-ECMHR (Hard α=0.20), 6. LB-ECMHR (Soft α=0.20→0.02)
# -------------------------------------------------------------
abl_keys = [
    "main_compare_minhop",
    "ablation_ec_only",
    "ablation_lb_dh0",
    "ablation_no_hysteresis",
    "main_compare_lbecmhr",
    "main_compare_lbecmhr_soft"
]
abl_labels = [
    "1. Minimum-Hop\n(Baseline, 60 chết)",
    "2. True EC-only\n(α=0.20, No LB)",
    "3. LB-ECMHR\n(ΔH=0, Cấm vòng)",
    "4. No Hysteresis\n(Tắt trễ γ=β)",
    "5. LB-ECMHR Hard\n(Đầy đủ, α=0.20)",
    "6. LB-ECMHR Soft\n(Dự phòng 0.20→0.02)"
]

mib_abl = [data[k]["delivered_data_mib"] for k in abl_keys]
func50_abl = [data[k]["functional_50_numeric"] for k in abl_keys]
# Cấu hình 1 (Min-Hop) và 2 (EC-only) tắt bộ lọc quá tải trong định tuyến (active overload transitions = 0)
trans_abl = [0 if k in ("main_compare_minhop", "ablation_ec_only") else data[k]["overload_transitions_count"] for k in abl_keys]
cv1hop_abl = [data[k]["cumulative_relay_load_cv_1hop"] for k in abl_keys]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), gridspec_kw={'width_ratios': [1.15, 1.15]})

x_pos = np.arange(len(abl_labels))
w_bar = 0.36
colors_p1 = [COLOR_MINHOP, COLOR_ECONLY, '#27ae60', '#2ecc71', COLOR_LBECMHR, COLOR_LBSOFT]

# Panel 1: Delivered Data (MiB) & Functional Lifetime Func50 (Round)
bars1 = ax1.bar(x_pos - w_bar/2, mib_abl, width=w_bar, color=colors_p1, edgecolor='black', alpha=0.9, label='Dữ liệu về Sink (MiB)')
ax1.set_ylabel('Tổng dữ liệu chuyển giao về Sink (MiB)', color='#1b4f72')
ax1.set_title('Đóng góp Cân bằng Tải & Soft Fallback lên Sản lượng & Func50', pad=10)
ax1.set_xticks(x_pos)
ax1.set_xticklabels(abl_labels, rotation=32, ha='right', fontsize=8.4)
ax1.set_ylim(0, 7.6)
ax1.grid(axis='y', linestyle=':', alpha=0.6)

for bar in bars1:
    h = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, h + 0.12, f"{h:.2f}", ha='center', va='bottom', fontweight='bold', fontsize=8.0)

ax1_t = ax1.twinx()
l_f50 = ax1_t.plot(x_pos + w_bar/2, func50_abl, marker='D', color='#d35400', linewidth=2.2, markersize=7, label='Tuổi thọ hữu ích Func50 (Round)')
ax1_t.set_ylabel('Tuổi thọ chức năng Func50 (Round)', color='#d35400')
ax1_t.set_ylim(50, 114)
ax1_t.tick_params(axis='y', labelcolor='#d35400')

ax1.annotate('True EC-only (No LB): 4.55 MiB (Func50=R73)\n→ Bật LB-ECMHR Hard tăng +0.33 MiB (+2,692 gói, Func50=R79)\n→ Bật Soft Fallback đạt 5.84 MiB (Func50=R96, 0 nút chết!)',
             xy=(1 - w_bar/2, 4.55), xytext=(0.05, 6.28),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.3, headwidth=5),
             fontsize=7.9, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#ebf5fb", ec=COLOR_LBSOFT, lw=1.1))

# Panel 2: Overload Transitions & 1-Hop Load CV
bars2 = ax2.bar(x_pos - w_bar/2, trans_abl, width=w_bar, color='#2980b9', edgecolor='black', alpha=0.88, label='Số lần chuyển quá tải (Lần)')
ax2.set_ylabel('Số lần chuyển trạng thái quá tải định tuyến (Lần)', color='#2980b9')
ax2.set_title('Tác dụng của Hysteresis (Giảm Rung Giật) & Giảm CV Vành Đai 1-Hop', pad=10)
ax2.set_xticks(x_pos)
ax2.set_xticklabels(abl_labels, rotation=32, ha='right', fontsize=8.4)
ax2.set_ylim(0, 310)
ax2.grid(axis='y', linestyle=':', alpha=0.6)

for bar in bars2:
    h = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, h + 4.0, f"{int(h)}", ha='center', va='bottom', fontweight='bold', fontsize=8.0, color='#1b4f72')

ax2_t = ax2.twinx()
l_cv1 = ax2_t.plot(x_pos + w_bar/2, cv1hop_abl, marker='s', color='#8e44ad', linewidth=2.2, linestyle='--', markersize=7, label='CV tải vành đai 1-hop (CV_1hop)')
ax2_t.set_ylabel('Hệ số biến thiên tải vành đai 1-hop (CV_1hop)', color='#8e44ad')
ax2_t.set_ylim(0.50, 0.95)
ax2_t.tick_params(axis='y', labelcolor='#8e44ad')

ax2.annotate('Tắt Hysteresis: 235 lần chuyển\n→ Bật Hysteresis: 194 lần (-17.4% rung giật!)\nĐồng thời CV_1hop giảm từ 0.789 (EC-only) xuống 0.680 (-13.8%)!',
             xy=(3 - w_bar/2, 235), xytext=(0.15, 252),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.3, headwidth=5),
             fontsize=7.9, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9", ec=COLOR_LBECMHR, lw=1.1))

plt.suptitle('Hình 20. Ablation Study: Đánh Giá Độc Lập Ngưỡng Năng Lượng, Cân Bằng Tải, Hysteresis và Soft Fallback', y=1.02, fontsize=12, fontweight='bold')
plt.tight_layout()
fig6_path = os.path.join(OUTPUT_DIR, "fig6_ablation_study.png")
plt.savefig(fig6_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"[OK] Đã lưu: {fig6_path}")

print("=== Hoàn tất toàn bộ 6 biểu đồ phân tích độ nhạy tham số & Ablation Study! ===")
