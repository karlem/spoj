"""Direct real-HF numerical oracle, never reconstructed from shard math."""

import torch


def baseline(block, x):
    with torch.inference_mode():
        return block(x)
