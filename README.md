# Wireless Sensor Network (WSN) Simulator

A modular, high-performance, round-based Wireless Sensor Network (WSN) simulator developed in Python. Designed for researching multi-hop communications, minimum-hop and energy-aware routing protocols (LB-ECMHR), radio energy consumption models, network lifetime evaluation, environmental telemetry (ELQI), and lightweight packet encryption (AES-128-CCM).

Includes an interactive **Streamlit** dashboard with **Plotly WebGL** topology visualization, deterministic simulation checkpointing, and real-time telemetry metrics.

---

## Key Features

- **Realistic Deployment & Heterogeneous Sensors**:
  - Simulates an area of $2000 \times 2000\text{ m}$ with 500 randomly deployed sensor nodes and 1 centrally located Sink node $(1000, 1000)$.
  - 5 sensor types: Temperature, Humidity, PM2.5, Wind, and Water Quality (100 nodes each).
- **Geometric Neighbor Graph & Topology Analysis**:
  - Distance-based communication graph with configurable transmission range ($R = 250\text{ m}$).
  - Computes connectivity ratio, direct sink neighbors, isolated nodes, and average node degree.
- **Routing Protocols**:
  - **Baseline Minimum-Hop Routing**: Shortest-path Dijkstra / BFS route discovery bypassing dead nodes (`DEAD`).
  - **Load-Balanced Energy-Constrained Minimum-Hop Routing (LB-ECMHR)**: Avoids overloaded relays using rolling-window load tracking and hysteresis, while penalizing low-energy nodes (`LOW_ENERGY`) and bounding detours ($\le 1$ extra hop).
- **First-Order Radio Energy Model (Heinzelman Model)**:
  - Free-space ($\epsilon_{fs}$) and multipath fading ($\epsilon_{mp}$) propagation models with threshold distance $d_0 = \sqrt{\epsilon_{fs} / \epsilon_{mp}}$.
  - Tracks transmission ($E_{TX}$) and reception ($E_{RX}$) energy per packet across each individual hop.
  - Dynamic battery depletion and state transitions: `ALIVE`, `LOW_ENERGY` (threshold $\le 15\%$), and `DEAD` ($E \le 0$).
- **Lightweight Packet Encryption (AES-128-CCM-8)**:
  - **End-to-End Security**: Sensor nodes encrypt measurements with AES-128-CCM and generate an 8-byte authentication tag; the Sink node decrypts and verifies integrity before data ingestion.
  - **Transparent Relay Forwarding**: Intermediate relays perform pure forwarding without per-hop decryption/re-encryption, eliminating cryptographic delay and CPU battery drain at relays.
  - **Zero-Overhead Nonce Construction**: 13-byte Nonce is deterministically reconstructed at Sink from packet header (`source_id` + `sequence_number`), requiring **0 additional bytes transmitted over the air**.
  - High-performance execution (~1.6 µs CPU latency per packet, ~600,000 packets/sec).
- **Environmental Data Generation & Quality Analysis (ELQI)**:
  - Spatiotemporally correlated generation for all 5 environmental parameters.
  - Inverse Distance Weighting (IDW) spatial interpolation and environmental living quality assessment (ELQI).
- **Simulation Checkpointing & Restore (`.wsnchk.gz`)**:
  - Atomic, gzip-compressed snapshot creation supporting hot save/restore.
  - Deterministic state persistence preserving random seeds, routing tables, and cryptographic keys.
- **Interactive Streamlit Web Dashboard**:
  - Live topology map powered by Plotly WebGL with interactive route tracing.
  - Real-time simulation controls (Run 1, 10, 50, or custom rounds).
  - Sidebar toggles for routing algorithms, environmental parameters, and **Packet Encryption**.
  - Real-time Data Transfer and Lightweight Security telemetry cards.

---

## Project Structure

```text
wsn-simulator/
│
├── app.py                          # Streamlit interactive web application
├── main.py                         # Baseline topology & routing inspection script
├── run_simulation.py               # Simulation script with CSV & plot export
├── run_energy_demo.py              # Energy and single/multi-round verification demo
├── run_environment_demo.py         # Environmental generation & ELQI verification demo
├── config.yaml                     # Central system configuration
├── SPECIFICATION.md                # System engineering specification
├── requirements.txt                # Project dependencies
│
├── core/                           # Core network entities
│   ├── network.py                  # WirelessSensorNetwork manager & graph analytics
│   ├── sensor.py                   # SensorNode model & battery states
│   ├── sink.py                     # SinkNode model
│   └── packet.py                   # Packet data structure with cryptographic metadata
│
├── data/                           # Data generation & security modules
│   ├── generator.py                # Environmental data generator
│   └── packet_crypto.py            # Lightweight AES-128-CCM packet encryption manager
│
├── routing/                        # Routing protocols
│   ├── minimum_hop.py              # Minimum-hop shortest path algorithm
│   ├── lb_ecmhr.py                 # Load-balanced ECMHR protocol implementation
│   ├── load_tracker.py             # Forwarding load tracker with hysteresis
│   └── route_manager.py            # Multi-algorithm route orchestration & caching
│
├── energy/                         # Energy dissipation models
│   └── radio_model.py              # First-order radio energy model (Heinzelman)
│
├── environment/                    # Environmental analytics
│   ├── collector.py                # Environmental data collector at Sink
│   ├── analyzer.py                 # Spatial interpolation (IDW) & ELQI engine
│   └── degradation.py              # Zone history tracker & degradation detector
│
├── simulation/                     # Simulation execution engine
│   ├── simulator.py                # WSNSimulator (round-based multi-hop execution)
│   ├── simulation_clock.py         # Simulated time & round duration mapper
│   └── checkpoint.py               # Gzip/pickle state persistence & restore
│
├── scripts/                        # Utility & benchmarking scripts
│   └── benchmark_packet_crypto.py  # 10,000-packet cryptographic latency benchmark
│
├── docs/                           # Technical documentation
│   └── README_PACKET_CRYPTO.md     # Detailed specification of AES-128-CCM-8
│
└── tests/                          # Automated unit test suite (75 tests passed)
    ├── test_deployment.py          # Deployment tests
    ├── test_neighbor_graph.py      # Topology & neighbor graph tests
    ├── test_minimum_hop.py         # Minimum-hop routing tests
    ├── test_radio_model.py         # Energy consumption tests
    ├── test_lb_ecmhr.py            # LB-ECMHR protocol tests
    ├── test_load_tracker.py        # Forwarding load tracking tests
    ├── test_packet_crypto.py       # Cryptography & tamper detection tests
    ├── test_checkpoint_determinism.py # Checkpoint determinism & restore tests
    └── test_simulator_metrics.py   # Simulation engine & telemetry tests
```

---

## Configuration (`config.yaml`)

Key parameters can be adjusted directly in `config.yaml`:

```yaml
network:
  width_m: 2000
  height_m: 2000
  num_sensors: 500
  random_seed: 42

sink:
  x: 1000
  y: 1000

energy:
  e_elec_nj_per_bit: 50         # Transmitter / Receiver electronics energy
  eps_fs_pj_per_bit_m2: 10       # Free space amplifier energy
  eps_mp_pj_per_bit_m4: 0.0013   # Multipath amplifier energy
  per_hop_delay_ms: 10           # Base processing delay per hop

sensor:
  initial_energy_j: 20.0        # Battery capacity (Joules)
  transmission_range_m: 250      # Communication radius (m)
  energy_threshold_ratio: 0.15   # 15% threshold for LOW_ENERGY state

packet:
  payload_size_bytes: 64        # Base payload size (bytes)
  sampling_interval_seconds: 10

routing:
  algorithm: "lb_ecmhr"         # "minimum_hop" or "lb_ecmhr"
  lb_ecmhr:
    load_window_rounds: 10
    overload_factor: 1.5
    recovery_factor: 1.1
    max_extra_hops: 1

packet_crypto:
  enabled: true                 # Toggle lightweight AES-128-CCM encryption
  algorithm: "aes_ccm_128"
  tag_bytes: 8                  # Authentication tag length
  header_bytes: 12
  cpu_energy_nj_per_byte: 1.2   # Sensor microcontroller CPU energy dissipation

checkpoint:
  auto_save: false
  interval_rounds: 500
  directory: "checkpoints"
  keep_last: 3
```

---

## Installation & Setup

### 1. Clone repository & create virtual environment
```bash
git clone https://github.com/haidangchv/wsn-simulator_beta.git
cd wsn-simulator_beta

python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

---

## Running the Application

### 1. Launch the Streamlit Interactive Dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501` to access:
- **Interactive Network Graph**: Inspect node states, links, and multi-hop paths.
- **Packet Encryption Control**: Toggle AES-128-CCM encryption on/off from the sidebar.
- **Telemetry Performance Cards**: Real-time monitoring of PDR, throughput, energy efficiency, encrypted packets, tag overhead, and verification rates.
- **Environmental & Living Quality Tabs**: Real-time IDW heatmaps, ELQI ratings, and degradation history.
- **Checkpoint Manager**: Save simulation snapshots and restore them with 1 click.

---

### 2. Run Automated Unit Tests
```bash
pytest
```
Currently passes **75 automated unit tests** across 10 test suites with 100% success rate:
- Deployment & Neighbor Graph tests
- Minimum-Hop & LB-ECMHR routing tests
- Radio energy model tests
- Checkpoint determinism & serialization tests
- AES-128-CCM-8 encryption, decryption, tamper detection, and zero-nonce tests

---

### 3. Cryptographic Latency Benchmark
To measure the raw CPU latency and throughput of the packet encryption module on your system:
```bash
python scripts/benchmark_packet_crypto.py
```

*Benchmark Sample Output (10,000 packets):*
```text
============================================================
    KẾT QUẢ BENCHMARK MÃ HÓA GÓI TIN (AES-128-CCM-8)
============================================================
  Số lượng mẫu thử nghiệm     : 10,000 packets
  Kích thước dữ liệu gốc      : 4 Bytes (float32)
  Kích thước sau mã hóa (tag) : 12 Bytes (+8 Bytes tag)
------------------------------------------------------------
  Thời gian mã hóa trung bình : 0.00167 ms/packet (1.67 µs)
  Tốc độ mã hóa (Throughput)  : ~598,000 packets/giây
------------------------------------------------------------
  Thời gian giải mã trung bình: 0.00159 ms/packet (1.59 µs)
  Tốc độ giải mã (Throughput) : ~628,000 packets/giây
============================================================
```

---

## Development Roadmap

- [x] **Stage 1**: Random sensor deployment & heterogeneous types
- [x] **Stage 2**: Geometric neighbor graph & topology analytics
- [x] **Stage 3**: Minimum-Hop shortest-path routing
- [x] **Stage 4**: First-order radio energy model & battery states
- [x] **Stage 5**: Round-based simulation engine & lifetime metrics (FND, HND, LND)
- [x] **Stage 6**: CSV exports & Matplotlib visualization curves
- [x] **Stage 7**: Streamlit interactive web dashboard with Plotly
- [x] **Stage 8**: Load-Balanced Energy-Constrained Minimum-Hop Routing (LB-ECMHR)
- [x] **Stage 9**: Environmental data generation (ELQI) & Lightweight packet encryption (AES-128-CCM-8)
- [ ] **Stage 10**: Security attack models (selective forwarding, packet tampering, blackhole) & trust defenses
- [ ] **Stage 11**: Clustering (LEACH / hybrid) & edge processing