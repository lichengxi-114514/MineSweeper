"""S3c 千局交叉验证：Game vs RefBoard，同一雷位 + 同一点击序列，逐次比对。

独立随机源（与 Game seed 解耦）驱动点击序列；
每次点击后断言 delta 相等、累计集合相等、逐格 adjacent 相等。
"""
from __future__ import annotations

import random

import pytest

from minesweeper.core import Game, GameState
from tests.reference import RefBoard


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _neighbors(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                result.append((nr, nc))
    return result


def _pick(
    crng: random.Random,
    g: Game,
    revealed: set[tuple[int, int]],
    flagged: set[tuple[int, int]],
) -> tuple[int, int] | None:
    candidates_frontier = [
        (r, c)
        for r in range(g.rows)
        for c in range(g.cols)
        if (r, c) not in revealed
        and (r, c) not in flagged
        and any(
            (nr, nc) in revealed
            for nr, nc in _neighbors(r, c, g.rows, g.cols)
        )
    ]
    everything = [
        (r, c)
        for r in range(g.rows)
        for c in range(g.cols)
        if (r, c) not in revealed and (r, c) not in flagged
    ]
    pool = (
        candidates_frontier
        if crng.random() < 0.7 and candidates_frontier
        else everything
    )
    return crng.choice(pool) if pool else None


def _run_game(
    seed: int, rows: int, cols: int, mines: int, max_clicks: int
) -> tuple[GameState, frozenset[tuple[int, int]]]:
    g = Game(rows, cols, mines, seed=seed)
    crng = random.Random(seed * 7919 + 13)

    first = (rows // 2, cols // 2)
    delta = g.reveal(*first)
    ref = RefBoard(rows, cols, g.snapshot_mines())
    ref_delta = ref.expand(*first)

    prev: set[tuple[int, int]] = set()
    assert set(g.revealed_cells) == set(ref.revealed_numbers())
    assert set(delta) == set(g.revealed_cells) - prev
    assert set(ref_delta) == set(delta)

    for _ in range(max_clicks):
        if g.state is not GameState.PLAYING:
            break
        cell = _pick(crng, g, set(g.revealed_cells), set())
        if cell is None:
            break

        prev = set(g.revealed_cells)
        delta = g.reveal(*cell)
        ref_delta = ref.expand(*cell)

        assert set(g.revealed_cells) == set(ref.revealed_numbers()), (
            f"seed={seed} cell={cell} 累计集合不一致"
        )
        assert set(delta) == set(g.revealed_cells) - prev, (
            f"seed={seed} cell={cell} delta 与差集不一致"
        )
        assert set(ref_delta) == set(delta), (
            f"seed={seed} cell={cell} 两侧 delta 不一致"
        )

        rn = ref.revealed_numbers()
        for rc in g.revealed_cells:
            assert g.view(*rc).adjacent == rn[rc], (
                f"seed={seed} cell={cell} {rc} 邻域数不一致"
            )

        if g.state is GameState.LOST:
            assert delta == [cell], f"seed={seed} 踩雷应只返回该格"
            break

    if g.state is GameState.WON:
        assert len(g.revealed_cells) == rows * cols - mines
    return g.state, g.revealed_cells


# ---------------------------------------------------------------------------
# 测试（共 6 条）
# ---------------------------------------------------------------------------

def test_cross_validation_9x9_1000_games():
    for seed in range(1000):
        _run_game(seed, 9, 9, 10, 40)


def test_cross_validation_16x16_200_games():
    for seed in range(200):
        _run_game(seed, 16, 16, 40, 60)


def test_crossval_zero_mines_win():
    for seed in range(5):
        g = Game(9, 9, 0, seed=seed)
        first = (4, 4)
        delta = g.reveal(*first)
        ref = RefBoard(9, 9, g.snapshot_mines())
        ref_delta = ref.expand(*first)

        assert g.state is GameState.WON
        assert len(g.revealed_cells) == 81
        assert set(g.revealed_cells) == set(ref.revealed_numbers())
        assert set(delta) == set(ref_delta)
        assert set(delta) == set(g.revealed_cells)

        rn = ref.revealed_numbers()
        for rc in g.revealed_cells:
            assert g.view(*rc).adjacent == rn[rc]


def test_crossval_mine_click_lost():
    for seed in range(50):
        g = Game(9, 9, 10, seed=seed)
        first = (4, 4)
        g.reveal(*first)
        layout = g.snapshot_mines()
        ref = RefBoard(9, 9, layout)
        ref.expand(*first)

        unrevealed_mines = layout - g.revealed_cells
        assert len(unrevealed_mines) > 0
        mine_cell = next(iter(unrevealed_mines))

        prev = set(g.revealed_cells)
        delta = g.reveal(*mine_cell)
        ref_delta = ref.expand(*mine_cell)

        assert g.state is GameState.LOST
        assert delta == [mine_cell]
        assert ref_delta == {mine_cell}
        assert set(g.revealed_cells) == set(ref.revealed_numbers())
        assert set(g.revealed_cells) - prev == {mine_cell}


def test_whole_run_deterministic():
    seeds = [0, 1, 42, 99, 500, 999]
    for seed in seeds:
        r1 = _run_game(seed, 9, 9, 10, 40)
        r2 = _run_game(seed, 9, 9, 10, 40)
        assert r1 == r2, f"seed={seed} 两次运行结果不一致"


def test_crossval_uses_only_public_api():
    with open(__file__, encoding="utf-8") as f:
        source = f.read()
    board_attr = "._" + "board"
    revealed_attr = "._" + "revealed"
    flagged_attr = "._" + "flagged"
    assert board_attr not in source, (
        f"本文件不应直接访问 {board_attr}"
    )
    assert revealed_attr not in source, (
        f"本文件不应直接访问 {revealed_attr}"
    )
    assert flagged_attr not in source, (
        f"本文件不应直接访问 {flagged_attr}"
    )
