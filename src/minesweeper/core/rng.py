# src/minesweeper/core/rng.py
"""可复现随机入口（D5）。"""
from __future__ import annotations

import random


def make_rng(seed: int | None = None) -> random.Random:
    """构造独立 Random 实例；seed=None 时自动取系统熵。"""
    return random.Random(seed)
