from dataclasses import dataclass
import math

import networkx as nx


@dataclass
class LBECMHRRouteResult:

    path: list

    hop_count: int

    total_distance_m: float

    bottleneck_energy_j: float

    max_relay_load: float

    baseline_hop_count: int

    detour_hops: int

    used_overload_fallback: bool

    used_low_energy_fallback: bool = False


@dataclass
class _PathLabel:

    path: list

    hop_count: int

    total_distance_m: float

    bottleneck_energy_j: float

    max_relay_load: float

    low_energy_relay_count: int = 0


class LBECMHRRouter:
    """
    Load-Balanced Energy-Constrained
    Minimum-Hop Routing.

    Priority:
    1. Relay energy > threshold (with optional Stage-2 soft reserve fallback)
    2. Avoid overloaded relays
    3. Minimum hop
    4. Minimum maximum relay load (when load_balancing_enabled=True)
    5. Maximum bottleneck residual energy (when load_balancing_enabled=True)
    6. Minimum physical distance

    Preferred route may use at most:
        H_min + max_extra_hops

    Otherwise fallback to the normal
    energy-eligible graph.
    """

    def __init__(
        self,
        network,
        energy_threshold_ratio: float,
        max_extra_hops: int = 1,
        allow_overload_fallback: bool = True,
        **kwargs
    ):

        self.network = network

        self.graph = network.graph

        self.sink = network.sink

        self.sink_id = (
            network.sink.node_id
        )

        self.sensor_map = {
            sensor.node_id: sensor
            for sensor
            in network.sensors
        }

        self.energy_threshold_ratio = float(
            energy_threshold_ratio
        )

        self.load_balancing_enabled = bool(
            kwargs.get("load_balancing_enabled", True)
        )

        self.allow_low_energy_fallback = bool(
            kwargs.get("allow_low_energy_fallback", False)
        )

        self.soft_energy_threshold_ratio = float(
            kwargs.get("soft_energy_threshold_ratio", 0.01)
        )

        self.max_extra_hops = (
            int(max_extra_hops)
            if self.load_balancing_enabled
            else 0
        )

        self.allow_overload_fallback = bool(
            allow_overload_fallback
        )

        self.candidate_k = int(
            kwargs.get("candidate_k", 6)
        )

        self._sink_neighbors = (
            list(self.graph.neighbors(self.sink_id))
            if self.sink_id in self.graph
            else []
        )

        self._graph_label_cache = {}

        self.candidate_routes = (
            self._precompute_candidate_routes()
        )

    # ==================================================
    # Geometry
    # ==================================================

    def _node_xy(
        self,
        node_id
    ):

        if node_id == self.sink_id:

            return (
                self.sink.x,
                self.sink.y
            )

        sensor = (
            self.sensor_map[
                node_id
            ]
        )

        return (
            sensor.x,
            sensor.y
        )

    def _distance(
        self,
        node_a,
        node_b
    ) -> float:

        ax, ay = self._node_xy(
            node_a
        )

        bx, by = self._node_xy(
            node_b
        )

        return math.hypot(
            ax - bx,
            ay - by
        )

    # ==================================================
    # Candidate Route Precomputation & Scoring
    # ==================================================

    def _precompute_candidate_routes(self) -> dict[int, list[list]]:
        """
        Precompute up to candidate_k acyclic paths to Sink for each sensor
        with hop count <= h_min + max_extra_hops using DAG traversal.
        """
        if self.sink_id not in self.graph:
            return {}

        dist = nx.single_source_shortest_path_length(
            self.graph,
            self.sink_id
        )

        adj = {
            node: list(self.graph.neighbors(node))
            for node in self.graph.nodes()
        }

        candidates = {}

        for sensor in self.network.sensors:
            sid = sensor.node_id
            if sid not in dist:
                candidates[sid] = []
                continue

            h_min = dist[sid]
            paths = []

            # Direct neighbor to sink
            if self.sink_id in adj.get(sid, []):
                paths.append([sid, self.sink_id])

            queue = [([sid], 0)]
            while queue and len(paths) < self.candidate_k:
                curr_path, extra_used = queue.pop(0)
                u = curr_path[-1]

                if u == self.sink_id:
                    if curr_path not in paths:
                        paths.append(curr_path)
                    continue

                d_u = dist.get(u, 999)
                nbrs = adj.get(u, [])

                # Downhill neighbors (closer to sink)
                downhill = [
                    v for v in nbrs
                    if dist.get(v, 999) == d_u - 1 and v not in curr_path
                ]
                downhill.sort(
                    key=lambda x: self._distance(x, self.sink_id)
                )

                for v in downhill[:3]:
                    queue.append((curr_path + [v], extra_used))

                # Level neighbors (same distance, detour +1)
                if extra_used < self.max_extra_hops:
                    level = [
                        w for w in nbrs
                        if dist.get(w, 999) == d_u and w not in curr_path
                    ]
                    level.sort(
                        key=lambda x: self._distance(x, self.sink_id)
                    )
                    for w in level[:2]:
                        queue.append((curr_path + [w], extra_used + 1))

            cand_records = []
            for p in paths:
                hop_count = len(p) - 1
                tot_dist = sum(self._distance(p[i], p[i + 1]) for i in range(len(p) - 1))
                relays = p[1:-1]
                cand_records.append((p, hop_count, tot_dist, relays))
            candidates[sid] = cand_records

        return candidates

    def _make_score(
        self,
        hop_count: int,
        max_load: float,
        bottleneck: float,
        tot_dist: float,
        low_energy_count: int = 0,
        is_soft_fallback: bool = False,
        path: list | None = None
    ) -> tuple:
        if not self.load_balancing_enabled:
            return (low_energy_count, hop_count, path or [])
        if is_soft_fallback:
            return (low_energy_count, hop_count, -bottleneck, max_load, tot_dist)
        return (hop_count, max_load, -bottleneck, tot_dist)

    def _route_source_from_candidates(
        self,
        source_id,
        load_factors: dict,
        overloaded_nodes: set,
        is_soft_fallback: bool = False
    ) -> LBECMHRRouteResult | None:
        """
        Score precomputed candidate routes for a source using current
        residual energy and load factors.
        """
        sensor = self.sensor_map.get(source_id)
        if sensor is None or not sensor.is_alive():
            return None

        # Direct connection to Sink
        if self.sink_id in self.graph.neighbors(source_id):
            return LBECMHRRouteResult(
                path=[source_id, self.sink_id],
                hop_count=1,
                total_distance_m=self._distance(source_id, self.sink_id),
                bottleneck_energy_j=sensor.remaining_energy,
                max_relay_load=0.0,
                baseline_hop_count=1,
                detour_hops=0,
                used_overload_fallback=False,
                used_low_energy_fallback=False
            )

        if not self.load_balancing_enabled:
            return None

        candidates = self.candidate_routes.get(source_id, [])
        if not candidates:
            return None

        h_min = min(cand[1] for cand in candidates)
        thr_ratio = (
            self.soft_energy_threshold_ratio
            if is_soft_fallback
            else self.energy_threshold_ratio
        )
        eff_overloaded = (
            overloaded_nodes
            if self.load_balancing_enabled
            else set()
        )

        preferred_cands = []
        fallback_cands = []

        for p, hop_count, tot_dist, relays in candidates:
            relay_invalid = False
            low_energy_count = 0
            for r in relays:
                s_r = self.sensor_map.get(r)
                if (
                    s_r is None
                    or not s_r.is_alive()
                    or s_r.remaining_energy <= s_r.initial_energy * thr_ratio
                ):
                    relay_invalid = True
                    break
                if s_r.remaining_energy <= s_r.initial_energy * self.energy_threshold_ratio:
                    low_energy_count += 1

            if relay_invalid:
                continue

            max_load = max([float(load_factors.get(r, 0.0)) for r in relays], default=0.0)
            bottleneck = min([self.sensor_map[r].remaining_energy for r in relays], default=sensor.remaining_energy)
            has_overload = any(r in eff_overloaded for r in relays)

            score = self._make_score(
                hop_count=hop_count,
                max_load=max_load,
                bottleneck=bottleneck,
                tot_dist=tot_dist,
                low_energy_count=low_energy_count,
                is_soft_fallback=is_soft_fallback,
                path=p
            )
            res = LBECMHRRouteResult(
                path=p,
                hop_count=hop_count,
                total_distance_m=tot_dist,
                bottleneck_energy_j=bottleneck,
                max_relay_load=max_load,
                baseline_hop_count=h_min,
                detour_hops=max(0, hop_count - h_min),
                used_overload_fallback=has_overload,
                used_low_energy_fallback=(is_soft_fallback and low_energy_count > 0)
            )

            if not has_overload and hop_count <= h_min + self.max_extra_hops:
                preferred_cands.append((score, res))
            elif self.allow_overload_fallback:
                fallback_cands.append((score, res))

        if preferred_cands:
            preferred_cands.sort(key=lambda x: x[0])
            return preferred_cands[0][1]
        elif fallback_cands:
            fallback_cands.sort(key=lambda x: x[0])
            return fallback_cands[0][1]

        return None

    # ==================================================
    # Relay eligibility
    # ==================================================

    def _is_energy_eligible(
        self,
        node_id,
        threshold_ratio: float | None = None
    ) -> bool:

        if node_id == self.sink_id:
            return True

        thr = (
            self.energy_threshold_ratio
            if threshold_ratio is None
            else threshold_ratio
        )

        sensor = (
            self.sensor_map[
                node_id
            ]
        )

        return (
            sensor.is_alive()
            and
            sensor.energy_ratio()
            >
            thr
        )

    def _sink_has_eligible_relay(
        self,
        threshold_ratio: float | None = None
    ) -> bool:
        return any(
            self._is_energy_eligible(nbr, threshold_ratio)
            for nbr in self._sink_neighbors
        )

    def _build_relay_graph(
        self,
        overloaded_nodes=None,
        exclude_overloaded=False,
        threshold_ratio: float | None = None
    ):

        overloaded_nodes = (
            (overloaded_nodes or set())
            if self.load_balancing_enabled
            else set()
        )

        eligible = {
            self.sink_id
        }

        for sensor in (
            self.network.sensors
        ):

            node_id = sensor.node_id

            if not self._is_energy_eligible(
                node_id,
                threshold_ratio=threshold_ratio
            ):

                continue

            if (
                exclude_overloaded
                and
                node_id
                in overloaded_nodes
            ):

                continue

            eligible.add(
                node_id
            )

        return (
            self.graph
            .subgraph(
                eligible
            )
        )

    # ==================================================
    # Dynamic programming labels from Sink
    # ==================================================

    def _build_labels(
        self,
        relay_graph,
        load_factors,
        is_soft_fallback: bool = False
    ):

        if (
            self.sink_id
            not in relay_graph
        ):

            return {}, {}

        distances = (
            nx.single_source_shortest_path_length(
                relay_graph,
                self.sink_id
            )
        )

        labels = {
            self.sink_id:
                _PathLabel(
                    path=[
                        self.sink_id
                    ],

                    hop_count=0,

                    total_distance_m=0.0,

                    bottleneck_energy_j=(
                        float("inf")
                    ),

                    max_relay_load=0.0,

                    low_energy_relay_count=0
                )
        }

        ordered_nodes = sorted(
            (
                node_id
                for node_id
                in distances
                if node_id
                !=
                self.sink_id
            ),

            key=lambda node_id:
                distances[node_id]
        )

        for node_id in ordered_nodes:

            node_distance = (
                distances[
                    node_id
                ]
            )

            sensor = (
                self.sensor_map[
                    node_id
                ]
            )

            node_load = float(
                load_factors.get(
                    node_id,
                    0.0
                )
            )

            is_low_energy_relay = (
                1
                if sensor.energy_ratio() <= self.energy_threshold_ratio
                else 0
            )

            candidates = []

            for neighbor in (
                relay_graph.neighbors(
                    node_id
                )
            ):

                if (
                    neighbor
                    not in distances
                ):
                    continue

                if (
                    distances[
                        neighbor
                    ]
                    !=
                    node_distance - 1
                ):
                    continue

                if neighbor not in labels:
                    continue

                next_label = (
                    labels[
                        neighbor
                    ]
                )

                total_distance = (
                    self._distance(
                        node_id,
                        neighbor
                    )
                    +
                    next_label
                    .total_distance_m
                )

                max_load = max(
                    node_load,
                    next_label
                    .max_relay_load
                )

                bottleneck = min(
                    sensor.remaining_energy,
                    next_label
                    .bottleneck_energy_j
                )

                low_count = (
                    is_low_energy_relay
                    +
                    next_label.low_energy_relay_count
                )

                label = _PathLabel(

                    path=(
                        [node_id]
                        +
                        next_label.path
                    ),

                    hop_count=(
                        1
                        +
                        next_label.hop_count
                    ),

                    total_distance_m=(
                        total_distance
                    ),

                    bottleneck_energy_j=(
                        bottleneck
                    ),

                    max_relay_load=(
                        max_load
                    ),

                    low_energy_relay_count=(
                        low_count
                    )
                )

                score = self._make_score(
                    hop_count=label.hop_count,
                    max_load=label.max_relay_load,
                    bottleneck=label.bottleneck_energy_j,
                    tot_dist=label.total_distance_m,
                    low_energy_count=label.low_energy_relay_count,
                    is_soft_fallback=is_soft_fallback,
                    path=label.path
                )

                candidates.append(
                    (
                        score,
                        label
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda item:
                        item[0]
                )

                labels[
                    node_id
                ] = (
                    candidates[0][1]
                )

        return (
            distances,
            labels
        )

    # ==================================================
    # Source may itself be LOW_ENERGY or overloaded.
    # Source can still originate its own packet.
    # ==================================================

    def _route_source(
        self,
        source_id,
        relay_graph,
        labels,
        is_soft_fallback: bool = False
    ):

        source = (
            self.sensor_map[
                source_id
            ]
        )

        if not source.is_alive():
            return None

        candidates = []

        # Source is NOT required to belong
        # to relay_graph.
        for neighbor in (
            self.graph.neighbors(
                source_id
            )
        ):

            if neighbor not in relay_graph:
                continue

            if neighbor not in labels:
                continue

            next_label = (
                labels[
                    neighbor
                ]
            )

            hop_count = (
                1
                +
                next_label.hop_count
            )

            total_distance = (
                self._distance(
                    source_id,
                    neighbor
                )
                +
                next_label
                .total_distance_m
            )

            # Source itself is not counted
            # as a relay.
            max_load = (
                next_label
                .max_relay_load
            )

            bottleneck = (
                next_label
                .bottleneck_energy_j
            )

            low_count = (
                next_label
                .low_energy_relay_count
            )

            if math.isinf(
                bottleneck
            ):

                # Direct Source -> Sink
                bottleneck = (
                    source.remaining_energy
                )

            result = LBECMHRRouteResult(

                path=(
                    [source_id]
                    +
                    next_label.path
                ),

                hop_count=(
                    hop_count
                ),

                total_distance_m=(
                    total_distance
                ),

                bottleneck_energy_j=(
                    bottleneck
                ),

                max_relay_load=(
                    max_load
                ),

                baseline_hop_count=(
                    hop_count
                ),

                detour_hops=0,

                used_overload_fallback=False,

                used_low_energy_fallback=(
                    is_soft_fallback and low_count > 0
                )
            )

            score = self._make_score(
                hop_count=result.hop_count,
                max_load=result.max_relay_load,
                bottleneck=result.bottleneck_energy_j,
                tot_dist=result.total_distance_m,
                low_energy_count=low_count,
                is_soft_fallback=is_soft_fallback,
                path=result.path
            )

            candidates.append(
                (
                    score,
                    result
                )
            )

        if not candidates:
            return None

        # Only shortest-hop candidates
        # are allowed at this stage.
        min_hops = min(
            item[1].hop_count
            for item
            in candidates
        )

        candidates = [
            item
            for item
            in candidates
            if item[1].hop_count
            ==
            min_hops
        ]

        candidates.sort(
            key=lambda item:
                item[0]
        )

        return candidates[0][1]

    def _resolve_via_graph(
        self,
        source_id,
        energy_graph,
        energy_labels,
        preferred_graph,
        preferred_labels,
        is_soft_fallback: bool = False
    ) -> LBECMHRRouteResult | None:
        baseline = self._route_source(
            source_id,
            energy_graph,
            energy_labels,
            is_soft_fallback=is_soft_fallback
        )
        if baseline is None:
            return None

        if not self.load_balancing_enabled:
            baseline.baseline_hop_count = baseline.hop_count
            baseline.detour_hops = 0
            baseline.used_overload_fallback = False
            return baseline

        preferred = self._route_source(
            source_id,
            preferred_graph,
            preferred_labels,
            is_soft_fallback=is_soft_fallback
        )

        if (
            preferred is not None
            and
            preferred.hop_count <= (baseline.hop_count + self.max_extra_hops)
        ):
            preferred.baseline_hop_count = baseline.hop_count
            preferred.detour_hops = (
                preferred.hop_count - baseline.hop_count
            )
            preferred.used_overload_fallback = False
            return preferred

        if self.allow_overload_fallback:
            baseline.baseline_hop_count = baseline.hop_count
            baseline.detour_hops = 0
            baseline.used_overload_fallback = True
            return baseline

        return None

    def _get_cached_graphs_and_labels(
        self,
        threshold_ratio: float,
        load_factors: dict,
        overloaded_nodes: set,
        is_soft_fallback: bool = False
    ):
        eligible_ids = frozenset(
            s.node_id
            for s in self.network.sensors
            if self._is_energy_eligible(s.node_id, threshold_ratio)
        )
        eff_overloaded = (
            frozenset(overloaded_nodes)
            if self.load_balancing_enabled
            else frozenset()
        )
        cache_key = (
            threshold_ratio,
            is_soft_fallback,
            eligible_ids,
            eff_overloaded
        )
        if cache_key in self._graph_label_cache:
            return self._graph_label_cache[cache_key]

        energy_graph = self._build_relay_graph(
            exclude_overloaded=False,
            threshold_ratio=threshold_ratio
        )
        _, energy_labels = self._build_labels(
            energy_graph,
            load_factors,
            is_soft_fallback=is_soft_fallback
        )

        if self.load_balancing_enabled:
            preferred_graph = self._build_relay_graph(
                overloaded_nodes=overloaded_nodes,
                exclude_overloaded=True,
                threshold_ratio=threshold_ratio
            )
            _, preferred_labels = self._build_labels(
                preferred_graph,
                load_factors,
                is_soft_fallback=is_soft_fallback
            )
        else:
            preferred_graph = energy_graph
            preferred_labels = energy_labels

        val = (energy_graph, energy_labels, preferred_graph, preferred_labels)
        self._graph_label_cache[cache_key] = val
        return val

    def route_source(
        self,
        source_id,
        load_factors=None,
        overloaded_nodes=None
    ) -> LBECMHRRouteResult | None:
        """
        Route a single source with load balancing and detour bounds.
        Tries fast candidate evaluation first before graph search.
        """
        load_factors = load_factors or {}
        overloaded_nodes = overloaded_nodes or set()

        sensor = self.sensor_map.get(source_id)
        if sensor is None or not sensor.is_alive():
            return None

        # Stage 1: Primary Energy Threshold (alpha)
        fast_result = self._route_source_from_candidates(
            source_id,
            load_factors,
            overloaded_nodes,
            is_soft_fallback=False
        )
        if fast_result is not None:
            return fast_result

        if self._sink_has_eligible_relay(self.energy_threshold_ratio):
            (
                energy_graph,
                energy_labels,
                preferred_graph,
                preferred_labels
            ) = self._get_cached_graphs_and_labels(
                threshold_ratio=self.energy_threshold_ratio,
                load_factors=load_factors,
                overloaded_nodes=overloaded_nodes,
                is_soft_fallback=False
            )

            stage1_res = self._resolve_via_graph(
                source_id,
                energy_graph,
                energy_labels,
                preferred_graph,
                preferred_labels,
                is_soft_fallback=False
            )
            if stage1_res is not None:
                return stage1_res

        # Stage 2: Optional Soft Reserve Fallback (alpha_soft)
        if self.allow_low_energy_fallback:
            fast_soft = self._route_source_from_candidates(
                source_id,
                load_factors,
                overloaded_nodes,
                is_soft_fallback=True
            )
            if fast_soft is not None:
                return fast_soft

            if self._sink_has_eligible_relay(self.soft_energy_threshold_ratio):
                (
                    soft_energy_graph,
                    soft_energy_labels,
                    soft_pref_graph,
                    soft_pref_labels
                ) = self._get_cached_graphs_and_labels(
                    threshold_ratio=self.soft_energy_threshold_ratio,
                    load_factors=load_factors,
                    overloaded_nodes=overloaded_nodes,
                    is_soft_fallback=True
                )

                stage2_res = self._resolve_via_graph(
                    source_id,
                    soft_energy_graph,
                    soft_energy_labels,
                    soft_pref_graph,
                    soft_pref_labels,
                    is_soft_fallback=True
                )
                if stage2_res is not None:
                    return stage2_res

        return None

    # ==================================================
    # Build all routes once per round
    # ==================================================

    def build_route_table(
        self,
        load_factors: dict,
        overloaded_nodes: set
    ) -> dict:
        """
        Build routes for all sources. Evaluates precomputed candidate routes first
        (10x-50x faster) and only triggers dynamic graph search for unresolved sources.
        """
        self._graph_label_cache.clear()
        route_table = {}
        unresolved = []

        for sensor in self.network.sensors:
            source_id = sensor.node_id
            if not sensor.is_alive():
                route_table[source_id] = None
                continue

            fast_route = self._route_source_from_candidates(
                source_id,
                load_factors,
                overloaded_nodes,
                is_soft_fallback=False
            )
            if fast_route is not None:
                route_table[source_id] = fast_route
            else:
                unresolved.append(source_id)

        # Stage 1 on-demand graph search ONLY if candidates could not resolve a live sensor
        still_unresolved = []
        if unresolved:
            if self._sink_has_eligible_relay(self.energy_threshold_ratio):
                energy_graph = self._build_relay_graph(
                    exclude_overloaded=False,
                    threshold_ratio=self.energy_threshold_ratio
                )
                _, energy_labels = self._build_labels(
                    energy_graph,
                    load_factors,
                    is_soft_fallback=False
                )

                if self.load_balancing_enabled:
                    preferred_graph = self._build_relay_graph(
                        overloaded_nodes=overloaded_nodes,
                        exclude_overloaded=True,
                        threshold_ratio=self.energy_threshold_ratio
                    )
                    _, preferred_labels = self._build_labels(
                        preferred_graph,
                        load_factors,
                        is_soft_fallback=False
                    )
                else:
                    preferred_graph = energy_graph
                    preferred_labels = energy_labels

                for source_id in unresolved:
                    res = self._resolve_via_graph(
                        source_id,
                        energy_graph,
                        energy_labels,
                        preferred_graph,
                        preferred_labels,
                        is_soft_fallback=False
                    )
                    if res is not None:
                        route_table[source_id] = res
                    else:
                        route_table[source_id] = None
                        still_unresolved.append(source_id)
            else:
                for source_id in unresolved:
                    route_table[source_id] = None
                    still_unresolved.append(source_id)

        # Stage 2: Soft Reserve Fallback when Stage 1 has no route
        if self.allow_low_energy_fallback and still_unresolved:
            soft_unresolved = []
            for source_id in still_unresolved:
                fast_soft = self._route_source_from_candidates(
                    source_id,
                    load_factors,
                    overloaded_nodes,
                    is_soft_fallback=True
                )
                if fast_soft is not None:
                    route_table[source_id] = fast_soft
                else:
                    soft_unresolved.append(source_id)

            if soft_unresolved and self._sink_has_eligible_relay(self.soft_energy_threshold_ratio):
                soft_energy_graph = self._build_relay_graph(
                    exclude_overloaded=False,
                    threshold_ratio=self.soft_energy_threshold_ratio
                )
                _, soft_energy_labels = self._build_labels(
                    soft_energy_graph,
                    load_factors,
                    is_soft_fallback=True
                )

                if self.load_balancing_enabled:
                    soft_pref_graph = self._build_relay_graph(
                        overloaded_nodes=overloaded_nodes,
                        exclude_overloaded=True,
                        threshold_ratio=self.soft_energy_threshold_ratio
                    )
                    _, soft_pref_labels = self._build_labels(
                        soft_pref_graph,
                        load_factors,
                        is_soft_fallback=True
                    )
                else:
                    soft_pref_graph = soft_energy_graph
                    soft_pref_labels = soft_energy_labels

                for source_id in soft_unresolved:
                    res = self._resolve_via_graph(
                        source_id,
                        soft_energy_graph,
                        soft_energy_labels,
                        soft_pref_graph,
                        soft_pref_labels,
                        is_soft_fallback=True
                    )
                    route_table[source_id] = res

        return route_table


def find_lb_ecmhr_route(
    network,
    source_id,
    energy_threshold_ratio: float = 0.20,
    load_factors: dict = None,
    overloaded_nodes: set = None,
    max_extra_hops: int = 1,
    allow_overload_fallback: bool = True
) -> LBECMHRRouteResult | None:
    """
    Convenience function for routing a single source with LB-ECMHR.
    """
    router = LBECMHRRouter(
        network=network,
        energy_threshold_ratio=energy_threshold_ratio,
        max_extra_hops=max_extra_hops,
        allow_overload_fallback=allow_overload_fallback
    )
    return router.route_source(
        source_id=source_id,
        load_factors=load_factors,
        overloaded_nodes=overloaded_nodes
    )
