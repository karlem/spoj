"""Small CPU experiment configuration; validate before allocating or spawning."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ExperimentConfig:
    hidden_size: int = 64
    moe_intermediate_size: int = 128
    num_experts: int = 4
    top_k: int = 2
    hidden_act: str = "silu"
    norm_topk_prob: bool = True
    seed: int = 0
    partitions: int = 2
    threads: int = 1
    startup_timeout: float = 60.0
    request_timeout: float = 10.0
    shutdown_timeout: float = 5.0
    # One worker ID for each expert in ascending expert order.
    placement: tuple[int, ...] | None = None

    def __post_init__(self):
        for name in ("hidden_size", "moe_intermediate_size", "num_experts", "threads"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.top_k) is not int or not 1 <= self.top_k <= self.num_experts:
            raise ValueError("require 1 <= top_k <= num_experts")
        if self.partitions != 2 or type(self.partitions) is not int:
            raise ValueError("exactly two worker partitions are required")
        if self.hidden_act != "silu" or type(self.norm_topk_prob) is not bool:
            raise ValueError("require silu and a boolean norm_topk_prob")
        if type(self.seed) is not int or not 0 <= self.seed < 2**63:
            raise ValueError("seed must be an integer in [0, 2**63)")
        for name in ("startup_timeout", "request_timeout", "shutdown_timeout"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
        if self.placement is not None:
            if not isinstance(self.placement, tuple) or len(self.placement) != self.num_experts:
                raise ValueError("placement must contain exactly one owner per expert")
            if any(type(owner) is not int or owner not in (0, 1) for owner in self.placement):
                raise ValueError("worker IDs must be 0 or 1")

    @property
    def owners(self) -> tuple[int, ...]:
        split = (self.num_experts + 1) // 2
        return self.placement if self.placement is not None else tuple(
            0 if expert < split else 1 for expert in range(self.num_experts)
        )
