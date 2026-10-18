"""Generic virtual scheduler, NOT a HeteroRouter reproduction or TCP benchmark."""
import json
import random
import statistics

SEED = 731
# Hypothetical replicas of IDENTICAL experts. Memory/setup costs are excluded.
ELIGIBLE = {0: (0, 1), 1: (1, 2), 2: (0, 2), 3: (0,), 4: (2,)}
TRUE = [  # bytes/s, RTT seconds, compute seconds per expert row: ALL ASSUMED
    {"bps": 12_500_000, "rtt": .002, "row_s": .001},
    {"bps": 1_250_000, "rtt": .030, "row_s": .0003},
    {"bps": 6_250_000, "rtt": .010, "row_s": .002},
]
PERCEIVED = [dict(x) for x in TRUE]
# Intentionally stale belief: device 1 was on a faster, lower-RTT connection.
PERCEIVED[1].update(bps=12_500_000, rtt=.002)


def reserve(cal, model, arrival, rows):
    """FIFO private full-duplex links + FIFO compute, no cross-device contention."""
    payload = 64 + rows * 64 * 4  # assumed header + CPU float32 hidden=64
    tx_start = max(arrival, cal[0])
    cal[0] = tx_start + payload / model["bps"]
    received = cal[0] + model["rtt"] / 2
    compute_start = max(received, cal[1])
    cal[1] = compute_start + rows * model["row_s"]
    rx_start = max(cal[1], cal[2])
    cal[2] = rx_start + payload / model["bps"]
    return cal[2] + model["rtt"] / 2


def workload():
    rng = random.Random(SEED)
    jobs = []
    for i in range(120):
        # Fixed semantic work shared by ALL policies: never substitute an expert.
        expert = rng.choices(range(5), weights=[5, 3, 2, 1, 1])[0]
        jobs.append((i * .008, expert, rng.choice([1, 4, 16, 32])))
    return jobs


def run(policy, perceived):
    actual = [[0., 0., 0.] for _ in TRUE]
    belief = [[0., 0., 0.] for _ in TRUE]
    counts = [0] * len(TRUE)
    rotation = {expert: 0 for expert in ELIGIBLE}
    latencies, ends = [], []
    for i, (arrival, expert, rows) in enumerate(workload()):
        allowed = ELIGIBLE[expert]
        predictions = {w: reserve(belief[w].copy(), perceived[w], arrival, rows)
                       for w in allowed}
        if policy == "first_eligible":
            worker = allowed[0]
        elif policy == "round_robin_eligible":
            worker = allowed[rotation[expert] % len(allowed)]
            rotation[expert] += 1
        elif policy == "predicted_earliest_finish":
            worker = min(allowed, key=lambda w: (predictions[w], w))
        else:
            raise ValueError(policy)
        assert worker in allowed
        reserve(belief[worker], perceived[worker], arrival, rows)
        end = reserve(actual[worker], TRUE[worker], arrival, rows)
        assert end >= arrival
        counts[worker] += 1
        latencies.append(end - arrival)
        ends.append(end)
    ordered = sorted(latencies)
    assert sum(counts) == len(workload())
    return {"policy": policy, "jobs": len(latencies), "worker_jobs": counts,
            "mean_s": statistics.mean(latencies),
            "p50_s": statistics.median(latencies),
            "p95_s_nearest_rank": ordered[(95 * len(ordered) + 99) // 100 - 1],
            "makespan_s": max(ends)}


def sanity():
    fast = {"bps": 1000., "rtt": .2, "row_s": .01}
    # rows=1 => 320 bytes each way: .32+.1+.01+.32+.1=.85 seconds.
    assert abs(reserve([0., 0., 0.], fast, 0., 1) - .85) < 1e-12
    slow = dict(fast, bps=500.)
    assert reserve([0., 0., 0.], slow, 0., 1) > .85
    c = [0., 0., 0.]
    first = reserve(c, fast, 0., 1)
    assert reserve(c, fast, 0., 1) > first
    assert run("predicted_earliest_finish", TRUE) == run("predicted_earliest_finish", TRUE)


if __name__ == "__main__":
    sanity()
    print(json.dumps({"status": "synthetic exploratory model; not measured",
        "seed": SEED, "metric_unit": "individual expert-batch job, not MoE request",
        "true_assumed": TRUE, "perceived_assumed": PERCEIVED,
        "hypothetical_identical_replicas": ELIGIBLE,
        "sanity_checks": "passed",
        "results": [run(p, PERCEIVED) for p in
                    ["first_eligible", "round_robin_eligible", "predicted_earliest_finish"]]
                   + [{**run("predicted_earliest_finish", TRUE),
                       "policy": "earliest_finish_with_true_parameters_non_oracle"}]},
        indent=2, sort_keys=True))
