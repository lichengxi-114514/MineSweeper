# tests/test_reference.py
"""RefBoard 参考实现测试：正常 / 边界 / 异常三节 + 证据性实验。"""
from __future__ import annotations

import pytest

from tests.reference import RefBoard


# ========== 正常 ==========

class TestNormal:
    """正常场景：验证展开语义与手算用例。"""

    def test_case_a_4x4_column_mines(self):
        """用例 A：4×4，第 1 列整列为雷，点击 (0,3) → 恰 8 格。"""
        mines = frozenset({(0, 1), (1, 1), (2, 1), (3, 1)})
        board = RefBoard(4, 4, mines)
        result = board.expand(0, 3)
        expected = {(0, 2), (0, 3), (1, 2), (1, 3), (2, 2), (2, 3), (3, 2), (3, 3)}
        assert result == expected
        # 左半 8 格不得出现
        for r in range(4):
            assert (r, 0) not in result
        # 雷格不得出现
        for m in mines:
            assert m not in result

    def test_case_b_click_nonzero_cell(self):
        """用例 B：同一盘面，点非零格 (1,0) → 恰 1 格。"""
        mines = frozenset({(0, 1), (1, 1), (2, 1), (3, 1)})
        board = RefBoard(4, 4, mines)
        result = board.expand(1, 0)
        assert result == {(1, 0)}

    def test_case_c_1x9_single_mine(self):
        """用例 C：1×9，单雷在 (0,4)，点击 (0,0) → 恰 4 格。"""
        mines = frozenset({(0, 4)})
        board = RefBoard(1, 9, mines)
        result = board.expand(0, 0)
        expected = {(0, 0), (0, 1), (0, 2), (0, 3)}
        assert result == expected

    def test_5x5_no_mines_center_click(self):
        """5×5 全无雷、点中心 → 25 格全翻开，revealed_numbers 全为 0。"""
        board = RefBoard(5, 5, frozenset())
        result = board.expand(2, 2)
        assert len(result) == 25
        numbers = board.revealed_numbers()
        assert all(v == 0 for v in numbers.values())

    def test_revealed_numbers_keys_match_expand(self):
        """revealed_numbers 的键集合 == 最近一次 expand 的返回集合。"""
        mines = frozenset({(0, 1), (1, 1), (2, 1), (3, 1)})
        board = RefBoard(4, 4, mines)
        result = board.expand(0, 3)
        assert board.revealed_numbers().keys() == result


# ========== 边界 ==========

class TestBoundary:
    """边界场景：极小棋盘、重复点击、雷格点击。"""

    def test_1x1_with_mine(self):
        """1×1 有雷 → {(0,0)}。"""
        board = RefBoard(1, 1, frozenset({(0, 0)}))
        result = board.expand(0, 0)
        assert result == {(0, 0)}

    def test_1x1_no_mine(self):
        """1×1 无雷 → {(0,0)} 且 adj==0。"""
        board = RefBoard(1, 1, frozenset())
        result = board.expand(0, 0)
        assert result == {(0, 0)}
        assert board.revealed_numbers()[(0, 0)] == 0

    def test_1x2_no_mines(self):
        """1×2 全无雷点 (0,0) → 2 格。"""
        board = RefBoard(1, 2, frozenset())
        result = board.expand(0, 0)
        assert result == {(0, 0), (0, 1)}

    def test_click_mine_cell_no_expand(self):
        """4×4 用例 A，点雷格 (1,1) → 返回 {(1,1)}，不展开。"""
        mines = frozenset({(0, 1), (1, 1), (2, 1), (3, 1)})
        board = RefBoard(4, 4, mines)
        result = board.expand(1, 1)
        assert result == {(1, 1)}
        # 不应传播到邻居
        assert (0, 0) not in result
        assert (0, 2) not in result

    def test_reclick_already_revealed(self):
        """重复点击已翻开的格 → 返回 set()，状态不变。"""
        board = RefBoard(3, 3, frozenset())
        result1 = board.expand(1, 1)
        assert len(result1) == 9  # 全翻开
        result2 = board.expand(1, 1)
        assert result2 == set()
        assert board.revealed_numbers().keys() == result1

    def test_reclick_mine_cell(self):
        """重复点击已翻开的雷格 → 返回 set()，状态不变。"""
        board = RefBoard(3, 3, frozenset({(1, 1)}))
        result1 = board.expand(1, 1)
        assert result1 == {(1, 1)}
        result2 = board.expand(1, 1)
        assert result2 == set()


# ========== 异常 ==========

class TestException:
    """异常场景：越界、非法参数。"""

    def test_expand_out_of_bounds(self):
        """expand(-1,0)、expand(0,9) → IndexError。"""
        board = RefBoard(4, 4, frozenset())
        with pytest.raises(IndexError):
            board.expand(-1, 0)
        with pytest.raises(IndexError):
            board.expand(0, 9)

    def test_adjacent_out_of_bounds(self):
        """adjacent(4,0) → IndexError。"""
        board = RefBoard(4, 4, frozenset())
        with pytest.raises(IndexError):
            board.adjacent(4, 0)

    def test_mine_cells_out_of_bounds(self):
        """mine_cells 含越界坐标 → ValueError，消息含该坐标。"""
        with pytest.raises(ValueError) as exc_info:
            RefBoard(3, 3, frozenset({(5, 5)}))
        assert "(5,5)" in str(exc_info.value)

    def test_invalid_board_size(self):
        """rows=0 或 cols=0 → ValueError。"""
        with pytest.raises(ValueError, match="棋盘尺寸必须 >= 1"):
            RefBoard(0, 3, frozenset())
        with pytest.raises(ValueError, match="棋盘尺寸必须 >= 1"):
            RefBoard(3, 0, frozenset())


# ========== 证据性实验 ==========

def test_experiment_recursion_limit_40x40():
    """固定递归上限后，本参考实现在 40×40 全 0 盘面触发 RecursionError，
    是正式实现选择迭代 BFS 的实测依据。"""
    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(1000)
    try:
        with pytest.raises(RecursionError):
            RefBoard(40, 40, frozenset()).expand(20, 20)
    finally:
        sys.setrecursionlimit(old)
