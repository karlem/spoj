"""The only module that knows the locked Hugging Face Qwen internal contract.

The state digest is independent of torch.save/pickle metadata: a version tag,
sorted names, length-prefixed JSON metadata, then little-endian float32 bytes.
"""

from dataclasses import dataclass
import hashlib
import json
import random
import struct

import torch
import torch.nn.functional as F
import transformers
from transformers.models.qwen3_moe import modeling_qwen3_moe as hf
from transformers.models.qwen3_moe.configuration_qwen3_moe import Qwen3MoeConfig

from .config import ExperimentConfig

SOURCE_SHA256 = "58387f2cc22a706e7e4c7dabe6cf05cb1e9c9fe48c57e2f2a0fc5cbdb2132f4f"


class CompatibilityError(RuntimeError):
    pass


def compatibility() -> dict:
    from pathlib import Path

    source_hash = hashlib.sha256(Path(hf.__file__).read_bytes()).hexdigest()
    if (torch.__version__, transformers.__version__, source_hash) != ("2.14.1", "5.20.1", SOURCE_SHA256):
        raise CompatibilityError("unsupported Qwen implementation; re-inspect and validate the adapter before changing the lock")
    return {"torch": torch.__version__, "transformers": transformers.__version__,
            "qwen_source_sha256": source_hash, "experts_backend": "eager"}


def configure_threads(threads: int):
    torch.set_num_threads(threads)
    # PyTorch permits setting inter-op only once; repeated sessions must match.
    if torch.get_num_interop_threads() != threads:
        try:
            torch.set_num_interop_threads(threads)
        except RuntimeError as exc:
            raise RuntimeError("set SPOI threads before starting inter-op work") from exc


def _hf_config(config):
    return Qwen3MoeConfig(hidden_size=config.hidden_size,
                         moe_intermediate_size=config.moe_intermediate_size,
                         num_experts=config.num_experts, num_experts_per_tok=config.top_k,
                         hidden_act=config.hidden_act, norm_topk_prob=config.norm_topk_prob,
                         experts_implementation="eager")


def _check_state(config, state):
    e, h, i = config.num_experts, config.hidden_size, config.moe_intermediate_size
    schema = {"gate.weight": (e, h), "experts.gate_up_proj": (e, 2*i, h),
              "experts.down_proj": (e, h, i)}
    if set(state) != set(schema):
        raise CompatibilityError(f"unexpected state keys: {sorted(state)}")
    for name, shape in schema.items():
        tensor = state[name]
        if tuple(tensor.shape) != shape or tensor.dtype != torch.float32 or tensor.device.type != "cpu":
            raise CompatibilityError(f"invalid {name}: require CPU float32 {shape}")
        if not torch.isfinite(tensor).all():
            raise CompatibilityError(f"nonfinite state: {name}")


def tensor_digest(tensors: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256(b"spoi-f32-state-v1\0")
    for name, tensor in sorted(tensors.items()):
        if tensor.device.type != "cpu" or tensor.dtype != torch.float32:
            raise ValueError("canonical digest requires CPU float32 tensors")
        metadata = json.dumps([name, "float32-le", list(tensor.shape)],
                              separators=(",", ":"), ensure_ascii=False).encode()
        digest.update(struct.pack("<Q", len(metadata)))
        digest.update(metadata)
        data = tensor.detach().contiguous().numpy().astype("<f4", copy=False).tobytes()
        digest.update(struct.pack("<Q", len(data)))
        digest.update(data)
    return digest.hexdigest()


@dataclass(frozen=True)
class ExpertShard:
    expert_ids: tuple[int, ...]
    gate_up: torch.Tensor
    down: torch.Tensor
    state_hash: str
    digest: str

    def actual_digest(self):
        # IDs are included so an equal-shaped permutation cannot pass.
        return tensor_digest({"ids:" + ",".join(map(str, self.expert_ids)) + ":gate_up": self.gate_up,
                              "down": self.down})

    @property
    def storage_bytes(self):
        return (self.gate_up.untyped_storage().nbytes(), self.down.untyped_storage().nbytes())


class FrozenState:
    """Own detached clones; exports always clone so callers cannot mutate the snapshot."""

    def __init__(self, config: ExperimentConfig, state: dict[str, torch.Tensor]):
        compatibility()
        _check_state(config, state)
        self.config = config
        self._state = {name: value.detach().clone().contiguous() for name, value in state.items()}
        self.hash = tensor_digest(self._state)

    def state_dict(self):
        return {name: value.clone() for name, value in self._state.items()}

    def router(self):
        router = hf.Qwen3MoeTopKRouter(_hf_config(self.config)).cpu().float().eval()
        router.load_state_dict({"weight": self._state["gate.weight"]})
        router.requires_grad_(False)
        return router

    def shard(self, worker_id: int):
        if worker_id not in (0, 1):
            raise ValueError("invalid worker")
        ids = tuple(e for e, owner in enumerate(self.config.owners) if owner == worker_id)
        # Advanced indexing plus explicit clone guarantees compact backing storage.
        gate = self._state["experts.gate_up_proj"][list(ids)].clone().contiguous()
        down = self._state["experts.down_proj"][list(ids)].clone().contiguous()
        shard = ExpertShard(ids, gate, down, self.hash, "")
        return ExpertShard(ids, gate, down, self.hash, shard.actual_digest())


def build_reference(config: ExperimentConfig):
    compatibility()
    configure_threads(config.threads)
    random.seed(config.seed)
    torch.manual_seed(config.seed)
    hf_config = _hf_config(config)
    block = hf.Qwen3MoeSparseMoeBlock(hf_config).cpu().float().eval()
    if block.experts.config._experts_implementation != "eager":
        raise CompatibilityError("Qwen experts backend is not eager")
    with torch.no_grad():
        for _, parameter in sorted(block.named_parameters()):
            parameter.normal_(mean=0.0, std=hf_config.initializer_range)
    block.requires_grad_(False)
    _check_state(config, block.state_dict())
    return block, FrozenState(config, block.state_dict())


def evaluate_shard(shard, rows, expert_ids, weights):
    """Return one weighted row per assignment using real fused Qwen slices."""
    output = torch.zeros_like(rows)
    if any(int(expert) not in shard.expert_ids for expert in expert_ids.unique()):
        raise ValueError("request names an expert not owned by this worker")
    for local, global_id in enumerate(shard.expert_ids):
        positions = (expert_ids == global_id).nonzero(as_tuple=True)[0]
        if not positions.numel():
            continue
        gate, up = F.linear(rows[positions], shard.gate_up[local]).chunk(2, dim=-1)
        values = F.linear(F.silu(gate) * up, shard.down[local])
        output[positions] = values * weights[positions, None]
    return output
