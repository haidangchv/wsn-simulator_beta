"""
Script: generate_sensitivity_figures.py
Description: Generates 6 publication-quality charts (PNG, 300 DPI) for the LB-ECMHR Parameter Sensitivity Analysis.
"""

import os
import json
import matplotlib.pyplot as plt
import numpy as np

# Set font and style for publication quality
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 14

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "..", "experiments", "sensitivity_results.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# -------------------------------------------------------------
# Biểu đồ 1: Energy Threshold alpha vs Connectivity Lifetime, Energy & PDR
# -------------------------------------------------------------
exp1 = data["exp1_alpha"]
alphas = [item["alpha"] for item in exp1]
conn_50 = [item["connectivity_50_round"] for item in exp1]
energies = [item["total_energy_consumed_j"] for item in exp1]
pdrs = [item["pdr"] for item in exp1]

fig, ax1 = plt.subplots(figsize=(8, 5))
color1 = '#1f77b4'
color2 = '#d62728'

ax1.set_xlabel('Hệ số ngưỡng năng lượng α (Energy Threshold Factor)', fontsize=12)
ax1.set_ylabel('Vòng đạt 50% kết nối (Connectivity 50% Round) & PDR (%)', color=color1, fontsize=11)
line1 = ax1.plot(alphas, conn_50, marker='s', color='#1f77b4', linewidth=2.2, markersize=8, label='Connectivity 50% Round')
line2 = ax1.plot(alphas, pdrs, marker='^', color='#2ca02c', linewidth=2.0, linestyle='--', markersize=7, label='PDR (%)')
ax1.tick_params(axis='y', labelcolor=color1)
ax1.set_ylim(60, 100)
ax1.grid(True, linestyle=':', alpha=0.6)

ax2 = ax1.twinx()
ax2.set_ylabel('Tổng năng lượng tiêu thụ (Joule)', color=color2, fontsize=11)
line3 = ax2.plot(alphas, energies, marker='o', color=color2, linewidth=2.2, markersize=8, label='Năng lượng tiêu thụ (J)')
ax2.tick_params(axis='y', labelcolor=color2)
ax2.set_ylim(200, 290)

# Mark optimal choice alpha = 0.20
ax1.axvline(x=0.20, color='gold', linestyle='-.', linewidth=2.5, alpha=0.8, label='Điểm chọn tối ưu (α = 0.20)')
ax1.annotate('Điểm tối ưu Pareto α = 0.20\n(Bảo vệ 20% pin, Năng lượng tối ưu)', 
             xy=(0.20, 79), xytext=(0.21, 65),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=6),
             fontsize=9.5, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#fff9c4", ec="#fbc02d", lw=1.5))

lines = line1 + line2 + line3
labels = [l.get_label() for l in lines] + ['Điểm chọn tối ưu (α = 0.20)']
ax1.legend(lines + [plt.Line2D([0],[0], color='gold', linestyle='-.', lw=2)], labels, loc='upper right', framealpha=0.9)

plt.title('Biểu đồ 1: Ảnh hưởng của Ngưỡng Năng lượng α đến Kết nối và Tiêu thụ Năng lượng')
plt.tight_layout()
fig1_path = os.path.join(OUTPUT_DIR, "fig1_alpha_sensitivity.png")
plt.savefig(fig1_path, dpi=300)
plt.close()
print(f"Saved: {fig1_path}")

# -------------------------------------------------------------
# Biểu đồ 2: Load Window W vs Relay Load CV & Overloaded Nodes
# -------------------------------------------------------------
exp2 = data["exp2_window"]
w_vals = [item["load_window_w"] for item in exp2]
cv_vals = [item["relay_load_cv"] for item in exp2]
ovl_nodes = [item["overloaded_relay_count"] for item in exp2]

fig, ax1 = plt.subplots(figsize=(8, 5))
color_bar = '#3498db'
color_line = '#e74c3c'

x_indices = np.arange(len(w_vals))
width = 0.35

bars = ax1.bar(x_indices - width/2, cv_vals, width, label='Relay Load CV', color=color_bar, edgecolor='black', alpha=0.85)
ax1.set_xlabel('Độ dài cửa sổ tải W (giờ / rounds)', fontsize=12)
ax1.set_ylabel('Hệ số biến thiên tải Relay (Relay Load CV)', color='#2980b9', fontsize=11)
ax1.set_xticks(x_indices)
ax1.set_xticklabels([f"{w}h" for w in w_vals])
ax1.set_ylim(0, 3.0)
ax1.tick_params(axis='y', labelcolor='#2980b9')
ax1.grid(True, linestyle=':', alpha=0.6, axis='y')

ax2 = ax1.twinx()
line = ax2.plot(x_indices + width/2, ovl_nodes, marker='D', color=color_line, linewidth=2.5, markersize=8, label='Số Relay Quá tải')
ax2.set_ylabel('Số Relay bị gán nhãn Overloaded', color=color_line, fontsize=11)
ax2.set_ylim(-5, 70)
ax2.tick_params(axis='y', labelcolor=color_line)

# Annotate W = 24
ax2.annotate('W = 24h: Chu kỳ ngày-đêm chuẩn\n(Nhận diện trúng 45 hotspot)', 
             xy=(2 + width/2, 45), xytext=(1.2, 53),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=6),
             fontsize=9.5, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#e8f8f5", ec="#1abc9c", lw=1.5))

plt.title('Biểu đồ 2: Ảnh hưởng của Cửa sổ Tải W đến Phân phối Tải và Phát hiện Hotspot')
fig.legend(loc='upper left', bbox_to_anchor=(0.14, 0.88), framealpha=0.9)
plt.tight_layout()
fig2_path = os.path.join(OUTPUT_DIR, "fig2_window_w_sensitivity.png")
plt.savefig(fig2_path, dpi=300)
plt.close()
print(f"Saved: {fig2_path}")

# -------------------------------------------------------------
# Biểu đồ 3: Overload Factor beta vs Relay Load CV & Average Hop
# -------------------------------------------------------------
exp3 = data["exp3_beta"]
betas = [item["beta"] for item in exp3]
cv_beta = [item["relay_load_cv"] for item in exp3]
ovl_beta = [item["overloaded_relay_count"] for item in exp3]
hops_beta = [item["average_hop_count"] for item in exp3]
energy_beta = [item["total_energy_consumed_j"] for item in exp3]

fig, ax1 = plt.subplots(figsize=(8, 5))
color_p = '#8e44ad'
color_e = '#d35400'

ax1.set_xlabel('Hệ số ngưỡng quá tải β (Overload Factor)', fontsize=12)
ax1.set_ylabel('Số Relay quá tải phát hiện & Relay Load CV', color=color_p, fontsize=11)
l1 = ax1.plot(betas, ovl_beta, marker='o', color='#8e44ad', linewidth=2.2, markersize=8, label='Số Relay Quá tải')
ax1.tick_params(axis='y', labelcolor=color_p)
ax1.set_ylim(20, 60)
ax1.grid(True, linestyle=':', alpha=0.6)

ax2 = ax1.twinx()
ax2.set_ylabel('Tổng năng lượng tiêu thụ (Joule)', color=color_e, fontsize=11)
l2 = ax2.plot(betas, energy_beta, marker='s', color='#d35400', linewidth=2.2, linestyle='--', markersize=8, label='Năng lượng tiêu thụ (J)')
ax2.tick_params(axis='y', labelcolor=color_e)
ax2.set_ylim(255.5, 257.5)

ax1.axvline(x=2.0, color='gold', linestyle='-.', linewidth=2.5, alpha=0.8)
ax1.annotate('β = 2.0: Điểm tối ưu\n(Năng lượng thấp nhất: 256.19 J)', 
             xy=(2.0, 45), xytext=(2.15, 48),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=6),
             fontsize=9.5, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#fef9e7", ec="#f39c12", lw=1.5))

lines = l1 + l2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper right', framealpha=0.9)

plt.title('Biểu đồ 3: Ảnh hưởng của Ngưỡng Quá tải β đến Relay Hotspot và Năng lượng')
plt.tight_layout()
fig3_path = os.path.join(OUTPUT_DIR, "fig3_beta_sensitivity.png")
plt.savefig(fig3_path, dpi=300)
plt.close()
print(f"Saved: {fig3_path}")

# -------------------------------------------------------------
# Biểu đồ 4: Recovery Factor gamma vs Hysteresis Margin
# -------------------------------------------------------------
exp4 = data["exp4_gamma"]
gammas = [item["gamma"] for item in exp4]
ovl_gamma = [item["overloaded_relay_count"] for item in exp4]
energy_gamma = [item["total_energy_consumed_j"] for item in exp4]

fig, ax = plt.subplots(figsize=(8, 5))
x_pos = np.arange(len(gammas))
bar_colors = ['#5dade2', '#48c9b0', '#2ecc71', '#f39c12']

bars = ax.bar(x_pos, ovl_gamma, width=0.45, color=bar_colors, edgecolor='black', alpha=0.85)
ax.set_xlabel('Hệ số phục hồi γ (với β = 2.0 cố định)', fontsize=12)
ax.set_ylabel('Số Relay duy trì trạng thái Overloaded', fontsize=11)
ax.set_xticks(x_pos)
ax.set_xticklabels([f"γ={g}\n(Đệm Δ={2.0-g:.1f})" for g in gammas])
ax.set_ylim(0, 60)
ax.grid(True, linestyle=':', alpha=0.6, axis='y')

for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.2, f"{int(yval)} nodes", ha='center', va='bottom', fontsize=9.5, fontweight='bold')

ax.annotate('γ = 1.2: Vùng đệm trễ lý tưởng (Δ = 0.8)\n(Chống rung giật Ping-Pong & phục hồi đúng lúc)', 
            xy=(2, 45), xytext=(0.8, 52),
            arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=6),
            fontsize=9.5, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#eafaf1", ec="#27ae60", lw=1.5))

plt.title('Biểu đồ 4: Ảnh hưởng của Ngưỡng Phục hồi Hysteresis γ đến Độ Ổn Định Trạng Thái')
plt.tight_layout()
fig4_path = os.path.join(OUTPUT_DIR, "fig4_gamma_hysteresis.png")
plt.savefig(fig4_path, dpi=300)
plt.close()
print(f"Saved: {fig4_path}")

# -------------------------------------------------------------
# Biểu đồ 5: Max Extra Hops Delta H vs Energy Consumption & Efficiency
# -------------------------------------------------------------
exp5 = data["exp5_delta_h"]
deltas = [str(item["delta_h"]) for item in exp5]
energies_delta = [item["total_energy_consumed_j"] for item in exp5]
efficiencies = [item["energy_efficiency"] for item in exp5]

fig, ax1 = plt.subplots(figsize=(8, 5))
color_b = '#2980b9'
color_r = '#c0392b'

x_inds = np.arange(len(deltas))
ax1.plot(x_inds, energies_delta, marker='o', color=color_r, linewidth=2.5, markersize=9, label='Năng lượng tiêu thụ (J)')
ax1.set_xlabel('Số hop đi vòng tối đa ΔH (Max Extra Hops)', fontsize=12)
ax1.set_ylabel('Tổng năng lượng tiêu thụ (Joule)', color=color_r, fontsize=11)
ax1.set_xticks(x_inds)
ax1.set_xticklabels([f"ΔH = {d}\n({'Không đi vòng' if d=='0' else 'Đi vòng 1 hop' if d=='1' else 'Đi vòng 2 hop'})" for d in deltas])
ax1.set_ylim(255.8, 257.0)
ax1.tick_params(axis='y', labelcolor=color_r)
ax1.grid(True, linestyle=':', alpha=0.6)

ax2 = ax1.twinx()
ax2.plot(x_inds, efficiencies, marker='^', color=color_b, linewidth=2.5, linestyle='--', markersize=9, label='Hiệu quả năng lượng (bit/J)')
ax2.set_ylabel('Hiệu quả năng lượng (bit/Joule)', color=color_b, fontsize=11)
ax2.set_ylim(168800, 169300)
ax2.tick_params(axis='y', labelcolor=color_b)

ax1.annotate('ΔH = 1: Năng lượng thấp nhất (256.19 J)\n(Hiệu quả tăng, né nghẽn mà không tốn hop vô ích)', 
             xy=(1, 256.19), xytext=(0.5, 256.65),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=6),
             fontsize=9.5, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#ebf5fb", ec="#2980b9", lw=1.5))

plt.title('Biểu đồ 5: Đánh Đổi giữa Số Hop Đi Vòng ΔH, Năng Lượng và Hiệu Quả Truyền')
fig.legend(loc='upper right', bbox_to_anchor=(0.88, 0.88), framealpha=0.9)
plt.tight_layout()
fig5_path = os.path.join(OUTPUT_DIR, "fig5_delta_h_tradeoff.png")
plt.savefig(fig5_path, dpi=300)
plt.close()
print(f"Saved: {fig5_path}")

# -------------------------------------------------------------
# Biểu đồ 6: Ablation Study - So sánh tổng hợp LB-ECMHR và Minimum-Hop
# -------------------------------------------------------------
ablation = data["ablation_study"]
labels = ["1. Minimum-Hop\n(Baseline)", "2. EC-only\n(alpha=0.2)", "3. Detour=0\n(Delta_H=0)", "4. No Hysteresis\n(gamma=1.99)", "5. Full LB-ECMHR\n(Đầy đủ)"]
dead_nodes = [item["dead_nodes"] for item in ablation]
energies_abl = [item["total_energy_consumed_j"] for item in ablation]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2))

# Subplot 1: Dead nodes
bars1 = ax1.bar(np.arange(len(labels)), dead_nodes, color=['#e74c3c', '#2ecc71', '#2ecc71', '#2ecc71', '#27ae60'], edgecolor='black', alpha=0.85)
ax1.set_ylabel('Số nút chết sau 100 rounds (Dead Nodes)', fontsize=11)
ax1.set_xticks(np.arange(len(labels)))
ax1.set_xticklabels(labels, rotation=25, ha='right', fontsize=9.5)
ax1.set_ylim(0, 75)
ax1.grid(True, linestyle=':', alpha=0.6, axis='y')
ax1.set_title('(a) Số Nút Chết do Energy Hole', fontsize=12, fontweight='bold')

for bar in bars1:
    y = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, y + 1.5, f"{int(y)} nút", ha='center', va='bottom', fontsize=9.5, fontweight='bold')

ax1.annotate('Energy Hole cục bộ!\n(60 nút quanh Sink cạn pin)', 
             xy=(0, 60), xytext=(0.3, 63),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=6),
             fontsize=9, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#fdedec", ec="#e74c3c", lw=1.5))

# Subplot 2: Energy consumed
bars2 = ax2.bar(np.arange(len(labels)), energies_abl, color=['#e67e22', '#3498db', '#3498db', '#3498db', '#2980b9'], edgecolor='black', alpha=0.85)
ax2.set_ylabel('Tổng năng lượng tiêu thụ toàn mạng (Joule)', fontsize=11)
ax2.set_xticks(np.arange(len(labels)))
ax2.set_xticklabels(labels, rotation=25, ha='right', fontsize=9.5)
ax2.set_ylim(230, 315)
ax2.grid(True, linestyle=':', alpha=0.6, axis='y')
ax2.set_title('(b) Tổng Năng Lượng Tiêu Thụ Toàn Mạng', fontsize=12, fontweight='bold')

for bar in bars2:
    y = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, y + 1.5, f"{y:.1f} J", ha='center', va='bottom', fontsize=9.5, fontweight='bold')

ax2.annotate('Tiết kiệm 40.35 J (-13.6%)\nNăng lượng thấp nhất: 256.19 J', 
             xy=(4, 256.19), xytext=(2.2, 290),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=6),
             fontsize=9, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="#ebf5fb", ec="#2980b9", lw=1.5))

plt.suptitle('Biểu đồ 6: So Sánh Tổng Hợp Nghiên Cứu Bóc Tách (Ablation Study) và Baseline', fontsize=13, fontweight='bold')
plt.tight_layout()
fig6_path = os.path.join(OUTPUT_DIR, "fig6_ablation_comparison.png")
plt.savefig(fig6_path, dpi=300)
plt.close()
print(f"Saved: {fig6_path}")

print("All 6 figures successfully generated!")
