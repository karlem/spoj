"""Bounded upstream-policy counterexamples, not an inference/network benchmark.

Inputs are constructed workloads and assumed service rates. Only upstream policy
execution, exhaustive enumeration and combinatorial arithmetic are observed.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import platform

SOURCE_SHA256 = "25b37ccd83aef2369c68f2b4bb596608a4f289956d97d9a3504bfd3159459e29"
SOURCE_REVISION = "d52c72d5b2f2fb4c41afbf8eb21366820239913d"


def score(owners, loads, rates, capacities):
    occupancy = [owners.count(i) for i in range(len(rates))]
    if any(n > cap for n, cap in zip(occupancy, capacities)):
        return None
    work = [sum(load for owner, load in zip(owners, loads) if owner == i)
            for i in range(len(rates))]
    times = [w / rate for w, rate in zip(work, rates)]
    return {"occupancy": occupancy, "device_service_work_units": times,
            "parallel_makespan_work_units": max(times),
            "sum_service_work_units": sum(times)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eplb-source", required=True, type=Path)
    args = parser.parse_args()
    data = args.eplb_source.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        parser.error("upstream source SHA256 mismatch; refusing to execute")
    import torch
    spec = importlib.util.spec_from_file_location("pinned_eplb", args.eplb_source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    loads = [100, 90, 10, 1]
    physical, _, counts = module.rebalance_experts(
        torch.tensor([loads], dtype=torch.float32), 4, 1, 2, 2)
    order = physical[0].tolist()
    assert sorted(order) == list(range(4))
    assert counts[0].tolist() == [1, 1, 1, 1]
    owners = [order.index(expert) // 2 for expert in range(4)]
    cases = []
    for name, rates, capacities in [
        ("equal_devices", [1, 1], [2, 2]),
        ("device0_tenfold_service", [10, 1], [2, 2]),
        ("device1_tenfold_service", [1, 10], [2, 2]),
        ("unequal_capacity_slots", [10, 1], [3, 1]),
    ]:
        feasible = [(a, score(list(a), loads, rates, capacities))
                    for a in itertools.product(range(2), repeat=4)]
        feasible = [(a, s) for a, s in feasible if s is not None]
        optimum = min(feasible, key=lambda x: (
            x[1]["parallel_makespan_work_units"], x[0]))
        cases.append({"name": name, "input_provenance": "constructed/assumed",
                      "loads": loads, "assumed_service_rates": rates,
                      "capacity_slots": capacities, "eplb_owners": owners,
                      "eplb_score": score(owners, loads, rates, capacities),
                      "feasible_assignments": len(feasible),
                      "finite_oracle_owners": list(optimum[0]),
                      "finite_oracle_score": optimum[1]})
    assert cases[0]["eplb_score"]["parallel_makespan_work_units"] == 101
    assert cases[0]["finite_oracle_score"]["parallel_makespan_work_units"] == 101
    assert cases[1]["eplb_score"]["parallel_makespan_work_units"] == 100
    assert cases[1]["finite_oracle_score"]["parallel_makespan_work_units"] == 19
    assert cases[3]["eplb_score"] is None
    assert cases[3]["finite_oracle_score"] is not None
    # Uniform independent per-layer top-k sampling is an explicit thought model.
    n, cold, topk, layers = 64, 1, 2, 32
    avoid_one = math.comb(n - cold, topk) / math.comb(n, topk)
    exposure = 1 - avoid_one ** layers
    assert 0.63 < exposure < 0.65
    print(json.dumps({
        "source_revision": SOURCE_REVISION, "source_sha256": SOURCE_SHA256,
        "environment": {"python": platform.python_version(), "torch": torch.__version__},
        "observed_upstream_physical_expert_order": order, "cases": cases,
        "cold_exposure_thought_model": {
            "experts_per_layer": n, "cold_experts_per_layer": cold,
            "topk": topk, "layers": layers,
            "assumption": "uniform top-k without replacement per layer; independent layers",
            "cold_placement_fraction": cold / n,
            "probability_token_requires_cold_tier": exposure},
        "limits": ["not measured device/link rates", "not MoE token end-to-end latency",
                   "no weights, model forward pass or generation", "no transport/hardware experiment",
                   "no proof of SPOJ speedup or application usefulness", "finite assignment oracle only",
                   "EPLB evaluated outside its equal-slot homogeneous-rate model; not an upstream bug claim"]
    }, indent=2) + "\n", end="")


if __name__ == "__main__":
    main()
