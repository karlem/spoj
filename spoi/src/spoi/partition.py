"""Preserve every original token and top-k slot across static expert ownership."""

from dataclasses import dataclass
import torch


@dataclass(frozen=True)
class Assignments:
    rows: torch.Tensor
    token_indices: torch.Tensor
    slot_indices: torch.Tensor
    expert_ids: torch.Tensor
    weights: torch.Tensor

    @property
    def count(self):
        return self.token_indices.numel()


def validate_input(x, hidden_size):
    if not isinstance(x, torch.Tensor) or x.ndim != 3 or x.shape[-1] != hidden_size:
        raise ValueError("input must have shape [batch, sequence, hidden_size]")
    if x.dtype != torch.float32 or x.device.type != "cpu" or not torch.isfinite(x).all():
        raise ValueError("input must be finite CPU float32")


def pack(x, selected, weights, owners):
    flat = x.reshape(-1, x.shape[-1])
    tokens = torch.arange(flat.shape[0]).unsqueeze(1).expand_as(selected)
    slots = torch.arange(selected.shape[1]).unsqueeze(0).expand_as(selected)
    ownership = torch.tensor(owners, dtype=torch.long)[selected]
    result = []
    for worker in (0, 1):
        mask = ownership == worker
        ti, si = tokens[mask].clone(), slots[mask].clone()
        result.append(Assignments(flat[ti].clone(), ti, si, selected[mask].clone(), weights[mask].clone()))
    return tuple(result)


def aggregate(shape, assignments, outputs):
    flat = torch.zeros((shape[0] * shape[1], shape[2]), dtype=torch.float32)
    for assignment, output in zip(assignments, outputs, strict=True):
        flat.index_add_(0, assignment.token_indices, output)
    return flat.reshape(shape)
