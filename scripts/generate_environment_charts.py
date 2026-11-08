import sys
from pathlib import Path
from copy import deepcopy
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.network import WirelessSensorNetwork
from topology.deployment import create_sink, deploy_sensors
from simulation.simulator import WSNSimulator
from environment.interpolation import create_idw_grid
from environment.analyzer import EnvironmentalAnalyzer

sys.stdout.reconfigure(encoding="utf-8")
plt.rcParams["font.sans-serif"] = ["Segoe UI", "DejaVu Sans", "Arial"]
plt.rcParams["axes.unicode_minus"] = False


class FastCollectorSlice:
    def __init__(self, gen_df: pd.DataFrame, rec_df: pd.DataFrame, up_to_round: int):
        self._gen_df = gen_df[gen_df["round"] <= up_to_round]
        self._rec_df = rec_df[rec_df["round"] <= up_to_round]
        self.generated_records = self._gen_df
        self.received_records = self._rec_df

    def received_dataframe(self) -> pd.DataFrame:
        return self._rec_df


def make_sim(base_cfg, alg, soft=False):
    cfg = deepcopy(base_cfg)
    cfg["sensor"]["initial_energy_j"] = 2.0
    cfg["sensor"]["transmission_range_m"] = 200.0
    cfg["sensor"]["energy_threshold_ratio"] = 0.20
    cfg["packet"]["payload_size_bytes"] = 128
    cfg["routing"]["algorithm"] = alg
    cfg["routing"]["energy_threshold_ratio"] = 0.20
    cfg["routing"]["lb_ecmhr"]["load_window_rounds"] = 24
    cfg["routing"]["lb_ecmhr"]["overload_factor"] = 2.0
    cfg["routing"]["lb_ecmhr"]["recovery_factor"] = 1.2
    cfg["routing"]["lb_ecmhr"]["max_extra_hops"] = 1
    cfg["routing"]["lb_ecmhr"]["allow_low_energy_fallback"] = soft
    cfg["routing"]["lb_ecmhr"]["soft_energy_threshold_ratio"] = 0.02 if soft else 0.20

    sensors = deploy_sensors(cfg)
    sink = create_sink(cfg)
    network = WirelessSensorNetwork(sensors=sensors, sink=sink)
    network.build_topology()
    return WSNSimulator(network=network, config=cfg, routing_algorithm=alg)


def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f)

    sims = {
        "min_hop": make_sim(base_cfg, "minimum_hop", soft=False),
        "lb_hard": make_sim(base_cfg, "lb_ecmhr", soft=False),
        "lb_soft": make_sim(base_cfg, "lb_ecmhr", soft=True),
    }
    analyzer = EnvironmentalAnalyzer(sims["lb_soft"].config)

    gen_dfs = {}
    rec_dfs = {}
    for k, s in sims.items():
        s.run(rounds=100)
        gen_dfs[k] = s.environment_collector.generated_dataframe()
        rec_dfs[k] = s.environment_collector.received_dataframe()

    conf_curves = {"min_hop": [], "lb_hard": [], "lb_soft": []}
    valid_zone_curves = {"min_hop": [], "lb_hard": [], "lb_soft": []}
    zone_snapshot_r66 = None

    for r in range(1, 101):
        for k in sims:
            sliced = FastCollectorSlice(gen_dfs[k], rec_dfs[k], r)
            zs = analyzer.build_zone_snapshot(sliced, r)
            conf_curves[k].append(float(zs["confidence"].mean()))
            valid_zone_curves[k].append(int((~zs["low_confidence"]).sum()))
            if k == "lb_soft" and r == 66:
                zone_snapshot_r66 = zs.copy()

    print(
        f"R66 (Peak Pollution Episode) Mean ELQI: {zone_snapshot_r66['elqi'].mean():.2f}, "
        f"Min: {zone_snapshot_r66['elqi'].min():.2f}, "
        f"Max: {zone_snapshot_r66['elqi'].max():.2f}"
    )
    print("R66 Ratings:", zone_snapshot_r66["rating"].value_counts().to_dict())
    for k in sims:
        print(
            f"{k} -> R78 conf={conf_curves[k][77]:.3f} (zones={valid_zone_curves[k][77]}), "
            f"R86 conf={conf_curves[k][85]:.3f} (zones={valid_zone_curves[k][85]}), "
            f"R95 conf={conf_curves[k][94]:.3f} (zones={valid_zone_curves[k][94]}), "
            f"R100 conf={conf_curves[k][99]:.3f} (zones={valid_zone_curves[k][99]})"
        )

    sliced_r66 = FastCollectorSlice(gen_dfs["lb_soft"], rec_dfs["lb_soft"], 66)

    # Figure 1: Spatial IDW Heatmaps (PM2.5, Temperature) & Zone ELQI Map at Round 66 (Peak Episode, 18:00 Rush Hour)
    fig1, axes = plt.subplots(1, 3, figsize=(16, 4.9), dpi=300)

    snap_pm25 = analyzer.latest_sensor_snapshot(sliced_r66, 66, "pm25")
    gx, gy, gz_pm25 = create_idw_grid(snap_pm25, 2000, 2000, resolution=70, power=2.0)
    im0 = axes[0].imshow(
        gz_pm25, extent=[0, 2000, 0, 2000], origin="lower", cmap="YlOrRd", aspect="equal"
    )
    axes[0].scatter(
        snap_pm25["x"], snap_pm25["y"], c="black", s=10, alpha=0.6, label="Sensor PM2.5 (100 nút)"
    )
    axes[0].set_title(
        "(a) Bản đồ nội suy IDW bụi mịn PM2.5 (µg/m³)\n(Điểm nóng KCN [1560,1360] & Giao thông [600,840])",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[0].set_xlabel("Tọa độ X (m)")
    axes[0].set_ylabel("Tọa độ Y (m)")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04, label="PM2.5 (µg/m³)")

    snap_temp = analyzer.latest_sensor_snapshot(sliced_r66, 66, "temperature")
    gx, gy, gz_temp = create_idw_grid(snap_temp, 2000, 2000, resolution=70, power=2.0)
    im1 = axes[1].imshow(
        gz_temp, extent=[0, 2000, 0, 2000], origin="lower", cmap="coolwarm", aspect="equal"
    )
    axes[1].scatter(
        snap_temp["x"], snap_temp["y"], c="black", s=10, alpha=0.6, label="Sensor Nhiệt độ (100 nút)"
    )
    axes[1].set_title(
        "(b) Bản đồ nội suy IDW Nhiệt độ (°C)\n(Đảo nhiệt đô thị [1400,660] & Vùng xanh [800,1500])",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[1].set_xlabel("Tọa độ X (m)")
    axes[1].set_ylabel("Tọa độ Y (m)")
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label="Nhiệt độ (°C)")

    elqi_grid = zone_snapshot_r66.pivot(index="row", columns="column", values="elqi").to_numpy()
    im2 = axes[2].imshow(
        elqi_grid,
        extent=[0, 2000, 0, 2000],
        origin="lower",
        cmap="RdYlGn",
        vmin=45,
        vmax=92,
        aspect="equal",
    )
    for _, z in zone_snapshot_r66.iterrows():
        if z["elqi"] < 68:
            axes[2].text(
                z["center_x"],
                z["center_y"],
                f"{z['zone_id']}\n{z['elqi']:.0f}",
                ha="center",
                va="center",
                fontsize=6.5,
                fontweight="bold",
                color="black",
            )
    axes[2].set_title(
        "(c) Bản đồ Chỉ số Chất lượng Sống ELQI (100 phân khu)\n(Định vị chính xác vùng suy giảm ELQI tại KCN Đông Bắc)",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[2].set_xlabel("Tọa độ X (m)")
    axes[2].set_ylabel("Tọa độ Y (m)")
    plt.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04, label="Điểm ELQI (0 - 100)")

    plt.tight_layout()
    plt.savefig("docs/figures/chart_env_spatial_elqi.png", dpi=300, bbox_inches="tight")
    plt.close(fig1)

    # Figure 2: Temporal 100-round cycles + Routing Impact on Zone Confidence
    fig2, (ax_t, ax_c) = plt.subplots(1, 2, figsize=(13.8, 5.0), dpi=300)

    df_rec = rec_dfs["lb_soft"]
    hourly_pm25 = df_rec[df_rec["sensor_type"] == "pm25"].groupby("round")["value"].mean()
    hourly_temp = df_rec[df_rec["sensor_type"] == "temperature"].groupby("round")["value"].mean()
    hourly_water = df_rec[df_rec["sensor_type"] == "water_quality"].groupby("round")["value"].mean()

    r_axis = np.arange(1, 101)
    ax_t.plot(
        r_axis,
        hourly_pm25.reindex(r_axis),
        color="#ef4444",
        lw=2.0,
        label="PM2.5 TB toàn mạng (µg/m³)",
    )
    ax_t.plot(
        r_axis,
        hourly_temp.reindex(r_axis),
        color="#f59e0b",
        lw=2.0,
        label="Nhiệt độ TB toàn mạng (°C)",
    )
    ax_t.plot(
        r_axis,
        hourly_water.reindex(r_axis),
        color="#0ea5e9",
        lw=1.8,
        linestyle="--",
        label="Chất lượng nước TB (Score 0-100)",
    )
    ax_t.axvspan(
        60, 96, color="#fee2e2", alpha=0.35, label="Đợt ô nhiễm giữa tuần (Pollution Episode)"
    )
    ax_t.set_title(
        "(a) Biến thiên chuỗi thời gian đa chỉ số môi trường (100 giờ = 4.2 ngày)\n(Chu kỳ ngày-đêm 24h, giờ cao điểm giao thông & tự tương quan AR(1) ρ=0.72)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax_t.set_xlabel("Round mô phỏng (1 Round = 1 Giờ)")
    ax_t.set_ylabel("Giá trị trung bình quan trắc")
    ax_t.grid(True, linestyle="--", alpha=0.4)
    ax_t.legend(loc="upper left", fontsize=8.5)

    ax_c.plot(
        r_axis,
        valid_zone_curves["min_hop"],
        color="#ef4444",
        lw=2.2,
        linestyle="--",
        label="Minimum-Hop (Đứt gãy ở R92 → rớt từ 100 xuống 9 Zones tin cậy)",
    )
    ax_c.plot(
        r_axis,
        valid_zone_curves["lb_hard"],
        color="#10b981",
        lw=2.2,
        linestyle="-.",
        label="LB-ECMHR Hard (Khóa ngưỡng cứng R79 → sau 6h hết hạn tươi dữ liệu ở R85)",
    )
    ax_c.plot(
        r_axis,
        valid_zone_curves["lb_soft"],
        color="#2563eb",
        lw=2.5,
        label="LB-ECMHR Soft (Duy trì 100/100 Zones đủ độ tin cậy tới tận R98)",
    )
    ax_c.axhline(
        50,
        color="#64748b",
        linestyle=":",
        lw=1.2,
        label="Ngưỡng 50% diện tích bản đồ đủ độ tin cậy (Conf ≥ 0.45)",
    )
    ax_c.set_title(
        "(b) Tác động của Định tuyến đến Số Phân Khu Đủ Độ Tin Cậy (Conf ≥ 0.45)\n(Cửa sổ độ tươi dữ liệu Freshness = 6 giờ, tổng cộng 100 Zones)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax_c.set_xlabel("Round mô phỏng (1 Round = 1 Giờ)")
    ax_c.set_ylabel("Số phân khu đạt chuẩn tin cậy (trên 100 Zones)")
    ax_c.set_ylim(-3, 106)
    ax_c.grid(True, linestyle="--", alpha=0.4)
    ax_c.legend(loc="lower left", fontsize=8.5)

    plt.tight_layout()
    plt.savefig("docs/figures/chart_env_temporal_routing_impact.png", dpi=300, bbox_inches="tight")
    plt.close(fig2)
    print("Saved environmental charts successfully!")


if __name__ == "__main__":
    main()
