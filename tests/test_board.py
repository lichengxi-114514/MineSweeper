# tests/test_board.py
"""Board 盘面层测试：正常 / 边界 / 异常三节。"""
from __future__ import annotations

import pytest

from minesweeper.core.board import Board
from minesweeper.core.rng import make_rng


# ========== 正常 ==========

class TestNormal:
    """正常场景：验证核心性质。"""

    def test_mine_count_and_adjacent_consistency(self):
        """9×9 / 10 雷：mine_count == 10；所有真实格 adjacent_at == count_adjacent_raw。"""
        board = Board(9, 9)
        rng = make_rng(42)
        board.place_mines(rng, 10)
        assert board.mine_count == 10
        for r in range(9):
            for c in range(9):
                assert board.adjacent_at(r, c) == board.count_adjacent_raw(r, c)

    def test_forbid_effect(self):
        """forbid 生效：protected_cells(4,4,9,9) 的 9 格 is_mine 全为 False（重复 100 次）。"""
        forbid = Board.protected_cells(4, 4, 9, 9)
        assert len(forbid) == 9
        for seed in range(100):
            board = Board(9, 9)
            rng = make_rng(seed)
            board.place_mines(rng, 10, forbid)
            for r, c in forbid:
                assert not board.is_mine(r, c)

    def test_seed_determinism(self):
        """同 seed 两次 place_mines → fingerprint 相同；不同 seed → 不同。"""
        b1 = Board(9, 9)
        b1.place_mines(make_rng(123), 10)
        b2 = Board(9, 9)
        b2.place_mines(make_rng(123), 10)
        assert b1.fingerprint() == b2.fingerprint()

        b3 = Board(9, 9)
        b3.place_mines(make_rng(456), 10)
        assert b1.fingerprint() != b3.fingerprint()

    def test_hex_roundtrip(self):
        """to_hex 往返：from_hex(to_hex()) 后 fingerprint 一致。"""
        for rows, cols, mines in [(1, 1, 0), (3, 3, 3), (9, 9, 10)]:
            board = Board(rows, cols)
            board.place_mines(make_rng(999), mines)
            hex_str = board.to_hex()
            restored = Board.from_hex(rows, cols, hex_str)
            assert restored.fingerprint() == board.fingerprint()

    def test_fingerprint_and_hex_length(self):
        """fingerprint 长度 == 2*(rows+2)*(cols+2)；to_hex 长度 == 2*rows*cols。"""
        for rows, cols in [(1, 1), (3, 5), (9, 9)]:
            board = Board(rows, cols)
            board.place_mines(make_rng(0), 0)
            assert len(board.fingerprint()) == 2 * (rows + 2) * (cols + 2)
            assert len(board.to_hex()) == 2 * rows * cols


# ========== 边界 ==========

class TestBoundary:
    """边界场景：极值、临界条件。"""

    def test_1x1_mines_0(self):
        """1×1：mines=0 成功。"""
        board = Board(1, 1)
        board.place_mines(make_rng(0), 0)
        assert board.mine_count == 0
        assert board.adjacent_at(0, 0) == 0

    def test_1x1_mines_1_with_forbid(self):
        """1×1：place_mines(rng,1,forbid={(0,0)}) 抛 ValueError。"""
        board = Board(1, 1)
        with pytest.raises(ValueError, match="候选不足"):
            board.place_mines(make_rng(0), 1, frozenset({(0, 0)}))

    def test_2x2_max_mines_at(self):
        """2×2：任意格 max_mines_at == 0。"""
        for r in range(2):
            for c in range(2):
                assert Board.max_mines_at(r, c, 2, 2) == 0

    def test_3x3_corner_and_center(self):
        """3×3：角 max_mines_at == 5，中心 == 0。"""
        assert Board.max_mines_at(0, 0, 3, 3) == 5
        assert Board.max_mines_at(1, 1, 3, 3) == 0

    def test_9x9_three_positions(self):
        """9×9：角 77 / 边上非角 75 / 内部 72。"""
        assert Board.max_mines_at(0, 0, 9, 9) == 77
        assert Board.max_mines_at(0, 4, 9, 9) == 75
        assert Board.max_mines_at(4, 4, 9, 9) == 72

    def test_protected_max_formula_and_bruteforce(self):
        """protected_max：min(rows,3)*min(cols,3)；与暴力版在 20 组尺寸上一致。"""
        for rows in range(1, 10):
            for cols in range(1, 10):
                if rows * cols > 20:
                    continue
                expected = min(rows, 3) * min(cols, 3)
                assert Board.protected_max(rows, cols) == expected
                brute = max(
                    len(Board.protected_cells(r, c, rows, cols))
                    for r in range(rows)
                    for c in range(cols)
                )
                assert expected == brute

    def test_neighbors_count_and_bounds(self):
        """neighbors：角 3 个、边上 5 个、内部 8 个；全部落在 [0,rows) × [0,cols)。"""
        board = Board(9, 9)
        assert len(list(board.neighbors(0, 0))) == 3
        assert len(list(board.neighbors(0, 4))) == 5
        assert len(list(board.neighbors(4, 4))) == 8
        for r in range(9):
            for c in range(9):
                for nr, nc in board.neighbors(r, c):
                    assert 0 <= nr < 9 and 0 <= nc < 9

    def test_high_density_corner(self):
        """高密度：9×9 角上首点、mines=77 成功；mines=78 抛 ValueError。"""
        forbid = Board.protected_cells(0, 0, 9, 9)
        board = Board(9, 9)
        board.place_mines(make_rng(0), 77, forbid)
        assert board.mine_count == 77

        board2 = Board(9, 9)
        with pytest.raises(ValueError, match="候选不足"):
            board2.place_mines(make_rng(0), 78, forbid)

    def test_neighbors_vs_offsets_cross_validation(self):
        """neighbors 与 _offsets 对所有格交叉验证（两套独立实现必须一致）。"""
        board = Board(5, 7)
        board.place_mines(make_rng(42), 10)
        for r in range(board.rows):
            for c in range(board.cols):
                off = board._off(r, c)
                offset_mines = sum(
                    board._mine[off + d] for d in board._offsets
                )
                neighbor_mines = sum(
                    1 for nr, nc in board.neighbors(r, c)
                    if board.is_mine(nr, nc)
                )
                assert offset_mines == neighbor_mines

    def test_mines_equals_candidates_boundary(self):
        """mines == 候选数的边界成功用例（3×3 角、mines=5）。"""
        forbid = Board.protected_cells(0, 0, 3, 3)
        board = Board(3, 3)
        board.place_mines(make_rng(0), 5, forbid)
        assert board.mine_count == 5

    def test_corner_single_mine_adjacent(self):
        """角上单雷时三个邻居的 adjacent_at == 1。"""
        board = Board(9, 9)
        board.place_mines(make_rng(0), 1, frozenset())
        if board.is_mine(0, 0):
            for nr, nc in board.neighbors(0, 0):
                assert board.adjacent_at(nr, nc) == 1

    def test_protected_cells_contains_self(self):
        """protected_cells 必须含自身。"""
        for rows, cols in [(3, 3), (5, 5), (9, 9)]:
            for r in range(rows):
                for c in range(cols):
                    cells = Board.protected_cells(r, c, rows, cols)
                    assert (r, c) in cells


# ========== 异常 ==========

class TestException:
    """异常场景：非法输入、违反契约。"""

    def test_place_mines_twice(self):
        """place_mines 重复调用 → RuntimeError。"""
        board = Board(9, 9)
        board.place_mines(make_rng(0), 10)
        with pytest.raises(RuntimeError, match="已布雷"):
            board.place_mines(make_rng(1), 10)

    def test_negative_mines(self):
        """mines=-1 → ValueError。"""
        board = Board(9, 9)
        with pytest.raises(ValueError, match="雷数不能为负"):
            board.place_mines(make_rng(0), -1)

    def test_mines_exceeds_candidates_message(self):
        """mines=候选格数+1 → ValueError，消息含三个数字。"""
        board = Board(3, 3)
        forbid = Board.protected_cells(0, 0, 3, 3)
        candidates = 9 - len(forbid)
        with pytest.raises(ValueError) as exc_info:
            board.place_mines(make_rng(0), candidates + 1, forbid)
        msg = str(exc_info.value)
        assert str(candidates + 1) in msg
        assert str(candidates) in msg
        assert str(len(forbid)) in msg

    def test_is_mine_out_of_bounds(self):
        """is_mine(-1,0)、is_mine(0,cols)、adjacent_at(rows,0) → IndexError。"""
        board = Board(9, 9)
        board.place_mines(make_rng(0), 10)
        with pytest.raises(IndexError):
            board.is_mine(-1, 0)
        with pytest.raises(IndexError):
            board.is_mine(0, 9)
        with pytest.raises(IndexError):
            board.adjacent_at(9, 0)

    def test_neighbors_out_of_bounds(self):
        """neighbors(-1,-1) → IndexError（不返回空迭代器）。"""
        board = Board(9, 9)
        with pytest.raises(IndexError):
            board.neighbors(-1, -1)

    def test_board_invalid_size(self):
        """Board(0,5)、Board(5,0) → ValueError。"""
        with pytest.raises(ValueError, match="棋盘尺寸必须 >= 1"):
            Board(0, 5)
        with pytest.raises(ValueError, match="棋盘尺寸必须 >= 1"):
            Board(5, 0)

    def test_from_hex_bad_length(self):
        """from_hex 五类坏样本之一：长度错误。"""
        with pytest.raises(ValueError, match="长度错误"):
            Board.from_hex(3, 3, "00")

    def test_from_hex_bad_hex_chars(self):
        """from_hex 五类坏样本之二：hex 字符错误。"""
        with pytest.raises(ValueError, match="hex 字符错误"):
            Board.from_hex(3, 3, "00000000000000000g")

    def test_from_hex_bad_mine_high_bits(self):
        """from_hex 五类坏样本之三：高 4 位 > 1。"""
        # byte at index 8 (cell 2,2) = 0x20 → high=2
        hex_str = "00" * 8 + "20"
        with pytest.raises(ValueError, match="高 4 位"):
            Board.from_hex(3, 3, hex_str)

    def test_from_hex_bad_adj_low_bits(self):
        """from_hex 五类坏样本之四：低 4 位 > 8。"""
        # 3x3 = 9 bytes = 18 hex chars. Byte at index 8 (cell 2,2) = 0x09 → low=9
        hex_str = "00" * 8 + "09"
        with pytest.raises(ValueError, match="低 4 位"):
            Board.from_hex(3, 3, hex_str)

    def test_from_hex_bad_adj_mismatch(self):
        """from_hex 五类坏样本之五：adj 与雷位重算不一致。"""
        # 3x3: mine at (0,0) → (0,1) should have adj=1, but we claim adj=3
        # byte 0 = 0x10 (mine=1, adj=0), byte 1 = 0x03 (mine=0, adj=3 but should be 1)
        bad_hex = "10" + "03" + "00" * 7
        with pytest.raises(ValueError, match="adj"):
            Board.from_hex(3, 3, bad_hex)
