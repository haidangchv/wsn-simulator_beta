# WSN Simulator Specification

Version: 0.6.0

## 1. Objective

Develop a modular, high-performance Wireless Sensor Network (WSN) simulator for studying:

- Multi-hop communication from sensor nodes to a central sink node
- Dynamic minimum-hop routing and topology adaptation
- Load-Balanced Energy-Constrained Minimum-Hop Routing (LB-ECMHR)
- First-order radio energy consumption modeling (Heinzelman model)
- Network lifetime evaluation (FND, HND, LND)
- Environmental data generation (spatiotemporal correlation) and ELQI living quality evaluation
- Lightweight packet encryption (AES-128-CCM with 8-byte tag) with zero-overhead nonce reconstruction
- State persistence and deterministic simulation checkpointing (`.wsnchk.gz`)
- Interactive web-based visualization and telemetry via Streamlit

---

## 2. Simulation Area

The simulated area is a rectangular region:

- Width: 2000 meters
- Height: 2000 meters

Coordinate system:

- $0 \le x \le 2000\text{ m}$
- $0 \le y \le 2000\text{ m}$

---

## 3. Sensor Network Deployment

Total number of sensor nodes:

- **500 nodes**, randomly deployed uniformly over the simulation area with a fixed random seed (default: `42`).

Each sensor data structure contains:

- Unique ID (`node_id`: $1 \dots 500$)
- Spatial coordinates (`x`, `y`)
- Sensor type (`sensor_type`)
- Battery specifications (`initial_energy`, `remaining_energy`, `consumed_energy_j`)
- Communication parameters (`transmission_range`, `neighbors`)
- Node state (`state`: `ALIVE`, `LOW_ENERGY`, `DEAD`)
- Relay capability flag (`relay_enabled`)
- Telemetry counters (`generated_packets`, `sent_packets`, `received_packets`, `forwarded_packets`, `transmitted_bytes`, `received_bytes`, `forwarded_bytes`)

---

## 4. Sensor Types

The network contains five heterogeneous environmental sensor types:

- 100 Temperature sensors
- 100 Humidity sensors
- 100 PM2.5 air-quality sensors
- 100 Wind sensors
- 100 Water-quality sensors

Total: **500 nodes**

---

## 5. Sink Node

Default sink position:

- $x = 1000\text{ m}$
- $y = 1000\text{ m}$
- `node_id = "SINK"`

The sink is assumed to have unlimited power and processing capabilities.

---

## 6. Energy Model

### 6.1 Battery Parameters
- Initial energy ($E_0$): **20.0 Joules** (configurable, default: 20.0 J)
- Low-energy threshold ratio: **15% - 20%** of initial energy ($E_{threshold}$)

### 6.2 Node States
- `ALIVE`: $E_{remaining} / E_0 > \text{threshold}$
- `LOW_ENERGY`: $0 < E_{remaining} / E_0 \le \text{threshold}$ (In baseline routing, remains a relay; in ECMHR/LB-ECMHR, avoided as relay)
- `DEAD`: $E_{remaining} \le 0$ (Node cannot generate packets or act as a relay; excluded from active routing graph)

### 6.3 Radio Model Equations (Heinzelman First-Order Model)
The radio model defines energy dissipation for transmitting ($E_{TX}$) and receiving ($E_{RX}$) a packet of $k$ bits over distance $d$:

$$d_0 = \sqrt{\frac{\epsilon_{fs}}{\epsilon_{mp}}} = \sqrt{\frac{10 \times 10^{-12}}{0.0013 \times 10^{-12}}} \approx 87.7\text{ m}$$

- **Transmission Energy ($E_{TX}$)**:
  $$E_{TX}(k, d) = \begin{cases} 
  k \cdot E_{elec} + k \cdot \epsilon_{fs} \cdot d^2 & \text{if } d < d_0 \\ 
  k \cdot E_{elec} + k \cdot \epsilon_{mp} \cdot d^4 & \text{if } d \ge d_0 
  \end{cases}$$

- **Reception Energy ($E_{RX}$)**:
  $$E_{RX}(k) = k \cdot E_{elec}$$

Parameters:
- $E_{elec} = 50\text{ nJ/bit}$
- $\epsilon_{fs} = 10\text{ pJ/bit/m}^2$
- $\epsilon_{mp} = 0.0013\text{ pJ/bit/m}^4$

When packet encryption is enabled, $k$ is calculated on the encrypted over-the-air packet size ($k = (\text{base\_payload} + \text{tag\_bytes}) \times 8$).

---

## 7. Communication & Neighbor Graph

- Default transmission range ($R$): **250 meters** (configurable: 50 – 400 m)
- Communication graph: Undirected geometric random graph $G = (V, E)$, where an edge $(u, v)$ exists if and only if:
  $$\text{dist}(u, v) \le R$$
- Graph analytics computed:
  - Average node degree
  - Number of edges
  - Connected sensors to sink
  - Isolated sensors
  - Direct sink neighbors
  - Connectivity ratio: $N_{connected} / N_{total}$

---

## 8. Packet Specification

- Base payload size: **64 bytes** (configurable in `config.yaml`)
- Encrypted payload size: **72 bytes** (+8 bytes authentication tag when AES-128-CCM is enabled)
- Packet fields:
  - `source_id`: Originating sensor ID
  - `sequence_number`: Monotonically increasing sequence number per sensor
  - `sensor_type`: Sensor telemetry category
  - `payload_size_bytes`: Active transmission size over the wireless channel (bytes)
  - `raw_payload_size_bytes`: Original plaintext payload size (bytes)
  - `created_round`: Round number when generated
  - `measurement_value`: Floating-point environmental measurement (or decrypted value at Sink)
  - `measurement_unit`: Physical unit (°C, %, µg/m³, m/s, index)
  - `route`: List of node IDs representing the transmission path
  - `hop_count`: Total hops from source to sink
  - `delivered`: Delivery success boolean
  - `delay_ms`: End-to-end latency (transmission + propagation + processing delay)
  - `dropped_reason`: Reason if dropped (`SOURCE_DEAD`, `NO_ROUTE`, `TX_ENERGY_INSUFFICIENT`, `RX_ENERGY_INSUFFICIENT`, `CRYPTO_AUTH_FAILED`)
  - `is_encrypted`: Boolean indicating whether packet payload is protected by AEAD
  - `ciphertext`: Encrypted payload including 8-byte authentication tag
  - `auth_tag_bytes`: Tag length (8 bytes)
  - `crypto_delay_ms`: Cryptographic CPU processing latency at sensor
  - `crypto_verified`: Integrity verification status at Sink (`True` / `False`)

---

## 9. Lightweight Packet Encryption (AES-128-CCM-8)

### 9.1 Mechanism & Cryptographic Primitives
- **Algorithm**: AES-128-CCM (Counter with CBC-MAC) specified by NIST SP 800-38C and RFC 3610.
- **Key**: 128-bit symmetric key (16 bytes) shared within the simulation domain.
- **Authentication Tag**: 8 bytes (balance between communication overhead and integrity protection).
- **Zero-Overhead Nonce Construction**: Nonce is 13 bytes, deterministically generated from packet header fields:
  - `source_id`: 4 bytes (uint32, big-endian)
  - `sequence_number`: 8 bytes (uint64, big-endian)
  - `direction / flag`: 1 byte (`0x00`)
  - **No per-packet Nonce transmission overhead** across the wireless channel.

### 9.2 End-to-End Operational Flow
1. **Sensor Node (Source)**:
   - Samples physical environmental indicator.
   - Encrypts measurement value into ciphertext + 8-byte tag via `PacketCrypto.encrypt_float32()`.
   - Payload size expands by exactly 8 bytes (`payload_size_bytes = base_payload + 8`).
   - Calculates sensor CPU computational energy ($E_{CPU} = \text{len} \times \text{cpu\_energy\_nj\_per\_byte}$).
2. **Relay Nodes (LB-ECMHR Forwarders)**:
   - Act as pure forwarders. Relays **do not decrypt or re-encrypt**, preventing per-hop cryptographic processing delay and battery drainage.
   - Radio transmission/reception energy accounts for the extra 8 bytes naturally through the first-order radio model.
3. **Sink Node (Destination)**:
   - Extracts `source_id` and `sequence_number` to reconstruct the 13-byte Nonce.
   - Verifies the 8-byte authentication tag and decrypts ciphertext via `PacketCrypto.decrypt_float32()`.
   - **Verification Passed**: Recovers original measurement value and submits packet to `EnvironmentalDataCollector`.
   - **Verification Failed**: Marks packet dropped with reason `CRYPTO_AUTH_FAILED`, increments `crypto_auth_failures`, and halts invalid data ingestion.

### 9.3 Checkpoint Safety & Determinism
- `PacketCrypto` implements explicit pickle serialization (`__getstate__` / `__setstate__`), persisting the raw 16-byte key and reconstructing the OpenSSL cipher context on restore.
- Seamlessly integrates with `.wsnchk.gz` simulation checkpoints without nonce reuse or cryptographic desynchronization.

---

## 10. Routing Protocols

1. **Baseline Minimum-Hop Routing**:
   - Shortest path calculated using hop count as weight via BFS / Dijkstra.
   - Dynamic rerouting: Dead nodes (`DEAD`) are pruned dynamically.
2. **Load-Balanced Energy-Constrained Minimum-Hop Routing (LB-ECMHR)**:
   - Dynamically avoids overloaded relay nodes based on rolling window packet forwarding tracking (`load_window_rounds`).
   - Hysteresis control: Nodal overload declared at $\ge 1.5\times$ mean load; recovery at $\le 1.1\times$ mean load.
   - Energy awareness: Bypasses `LOW_ENERGY` nodes when selecting candidate relay paths.
   - Max extra hops constraint: Allows bounded detours ($\le 1$ extra hop) to preserve energy and prevent hot-spot formation.

---

## 11. Simulation Execution Model

The simulator operates on a discrete, round-based execution model (1 round = 1 hour simulation time, 24 rounds/day):

### Round Execution Steps:
1. **Snapshot Alive Nodes**: Determine active nodes at round start.
2. **Route Refresh**: RouteManager evaluates active topology and computes multi-hop routes according to selected algorithm.
3. **Sequential Packet Generation & Encryption**: For each alive sensor:
   - Generate environmental measurement with spatiotemporal correlation.
   - If packet crypto is enabled: encrypt payload, append 8-byte tag, deduct microcontroller CPU energy.
   - For each hop along the path:
     - Deduct transmission energy $E_{TX}$ from sender.
     - Deduct reception energy $E_{RX}$ from receiver.
     - If energy is insufficient, packet is dropped (`TX_ENERGY_INSUFFICIENT` or `RX_ENERGY_INSUFFICIENT`).
   - Upon reaching Sink:
     - If packet crypto enabled: verify tag and decrypt. On tamper, drop with `CRYPTO_AUTH_FAILED`.
     - Record delivery, delay, hop count, and feed measurement to `EnvironmentalDataCollector`.
4. **Update Network Lifetime Metrics**: Record `FND`, `HND`, `LND`.
5. **Periodic Environmental Analysis & Degradation**: Spatial interpolation (IDW) and ELQI score calculations.
6. **Auto-Checkpointing**: Periodic rotation and saving of `.wsnchk.gz` snapshots if configured.

---

## 12. Metrics & Performance Indicators

| Metric | Formula / Definition | Unit |
| :--- | :--- | :--- |
| **PDR** (Packet Delivery Ratio) | $P_{delivered} / P_{generated}$ | $\%$ |
| **Throughput** | $(\text{Delivered Bytes} \times 8) / T_{elapsed}$ | kbps |
| **Average Delay** | $\sum \text{delay}_{delivered} / P_{delivered}$ | ms |
| **Average Hop Count** | $\sum \text{hops}_{delivered} / P_{delivered}$ | hops |
| **Energy Consumed** | Total energy dissipated across all nodes | Joules |
| **Residual Energy** | Total remaining battery across all nodes | Joules |
| **Energy Efficiency** | $(\text{Delivered Bytes} \times 8) / \text{Energy Consumed}$ | bit/J |
| **FND / HND / LND** | First / Half / Last Node Dead round index | round |
| **Encrypted Packets** | Count of packets encrypted at source sensors | packets |
| **Decrypted Packets** | Count of packets authenticated and decrypted at Sink | packets |
| **Auth Failures** | Count of packets failing tag verification | packets |
| **Crypto Overhead** | Total byte overhead added by auth tags ($8 \times P_{enc}$) | Bytes |
| **Avg Crypto Latency** | Mean CPU time for AES-CCM encryption and decryption | µs/packet |

---

## 13. Evaluation, Export & Interactive GUI

- **Streamlit Interactive Web UI (`app.py`)**:
  - Live Plotly WebGL network graph with interactive route tracing and link inspection.
  - Sidebar controls: Network dimensions, initial energy, transmission range, routing algorithms, environmental scenario parameters, and **Packet Encryption Toggle (AES-128-CCM)**.
  - Checkpoint Save & Restore (.wsnchk.gz) with integrity verification.
  - Dedicated telemetry cards for Data Transfer and Lightweight Security performance.
  - Heatmap visualizations and environmental degradation analysis tabs.