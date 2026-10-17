"""Offline random-weight smoke; no checkpoint or tokenizer is loaded."""

import argparse
from dataclasses import asdict
import json

import torch

from .baseline import baseline
from .config import ExperimentConfig
from .coordinator import ExpertSession
from .qwen3_adapter import build_reference, compatibility


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--hidden-size", type=int, default=64)
    smoke.add_argument("--moe-intermediate-size", type=int, default=128)
    smoke.add_argument("--num-experts", type=int, default=4)
    smoke.add_argument("--top-k", type=int, default=2)
    smoke.add_argument("--hidden-act", choices=["silu"], default="silu")
    smoke.add_argument("--norm-topk-prob", action=argparse.BooleanOptionalAction, default=True)
    smoke.add_argument("--seed", type=int, default=0)
    smoke.add_argument("--batch", type=int, default=1)
    smoke.add_argument("--sequence", type=int, default=16)
    smoke.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()
    if args.batch < 1 or args.sequence < 1:
        parser.error("batch and sequence must be positive")
    config = ExperimentConfig(**{key: value for key, value in vars(args).items()
                                 if key not in ("command", "batch", "sequence")})
    block, state = build_reference(config)
    generator = torch.Generator().manual_seed(config.seed + 100)
    x = torch.randn(args.batch, args.sequence, config.hidden_size, generator=generator)
    expected = baseline(block, x)
    with ExpertSession(config, state) as session:
        first = session.forward(x)  # Startup and first shared-memory copy are not steady state.
        result = session.forward(x)
        torch.testing.assert_close(first.output, expected, rtol=1e-5, atol=1e-6)
        torch.testing.assert_close(result.output, expected, rtol=1e-5, atol=1e-6)
        delta = (result.output - expected).abs()
        record = dict(config=asdict(config), versions=compatibility(), shape=list(x.shape),
                      dtype=str(x.dtype), device=str(x.device), finite=bool(torch.isfinite(result.output).all()),
                      state_hash=state.hash, workers=session.workers,
                      assignment_counts=result.assignment_counts, worker_compute_ns=result.worker_compute_ns,
                      startup_ns=session.startup_ns, persistent_worker_pids=session.worker_pids,
                      requests_completed=result.request_id,
                      max_absolute_error=delta.max().item(),
                      max_relative_error=(delta / expected.abs().clamp_min(1e-12)).max().item(),
                      tolerance=dict(rtol=1e-5, atol=1e-6))
    record["worker_exitcodes"] = session.exitcodes
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
