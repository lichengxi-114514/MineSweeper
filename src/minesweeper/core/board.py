# src/minesweeper/core/board.py
"""盘面数据层：雷位、邻域计数、边界处理。

坐标约定（重要）
----------------
对外公开接口一律 0-based：(r, c)，0 <= r < rows，0 <= c < cols。
内部为哨兵边框布局：真实格 (r, c) 的偏移为 (r+1)*W + (c+1)，W = cols + 2。
偏移换算只允许经 _off() 一处完成；其他任何地方出现 (r+1)*W 都属 bug。

设计依据见 docs/decisions.md D1–D6。
"""
from __future__ import annotations

import random
from typing import Iterator

MINE = 1
EMPTY = 0


class Board:
    rows: int
    cols: int

    def __init__(self, rows: int, cols: int) -> None:
        """分配含哨兵边框的空盘，不布雷。

        Raises:
            ValueError: rows < 1 或 cols < 1。
        """
        if rows < 1 or cols < 1:
            raise ValueError(f"棋盘尺寸必须 >= 1，收到 {rows}x{cols}")
        self.rows, self.cols = rows, cols
        self._w = cols + 2
        n = (rows + 2) * self._w
        self._mine = bytearray(n)      # 边框恒为 0
        self._adj = bytearray(n)       # 边框恒为 0
        self._mine_count = 0
        self._placed = False
        # 8 个固定偏移：因为有边框，偏移与位置无关，永远只有这一个元组
        self._offsets: tuple[int, ...] = (
            -self._w - 1, -self._w, -self._w + 1,
            -1, 1,
            self._w - 1, self._w, self._w + 1,
        )

    # ---------- 内部换算（唯一出口）----------
    def _off(self, r: int, c: int) -> int:
        """(r, c) -> 缓冲区偏移。调用前必须已验证 (r, c) 在界内。"""
        return (r + 1) * self._w + (c + 1)

    # ---------- 坐标与邻域 ----------
    def in_bounds(self, r: int, c: int) -> bool:
        """0-based 坐标是否落在真实格内。"""
        raise NotImplementedError

    def neighbors(self, r: int, c: int) -> Iterator[tuple[int, int]]:
        """生成已裁剪的合法邻居（0-based），绝不返回边框坐标。

        Raises:
            IndexError: (r, c) 本身越界。与 is_mine/adjacent_at 保持一致，
                不静默返回空迭代器（那会掩盖调用点错误）。

        注意：生成器只能迭代一次。热路径请直接迭代 self._offsets。
        """
        raise NotImplementedError

    # ---------- 首点保护（D3 / D6）----------
    @staticmethod
    def protected_cells(r: int, c: int, rows: int, cols: int) -> frozenset[tuple[int, int]]:
        """首点 (r,c) 的保护集 = 自身 ∪ 8 邻域（越界裁剪）。"""
        raise NotImplementedError

    @staticmethod
    def protected_max(rows: int, cols: int) -> int:
        """所有可能首点中保护集的最大值 = min(rows,3) * min(cols,3)。"""
        raise NotImplementedError

    @staticmethod
    def max_mines_at(r: int, c: int, rows: int, cols: int) -> int:
        """以 (r,c) 为首点时的单格上限 = rows*cols - len(protected_cells)。

        Raises:
            IndexError: (r,c) 越界。
        """
        raise NotImplementedError

    # ---------- 布雷 ----------
    def place_mines(
        self,
        rng: random.Random,
        mines: int,
        forbid: frozenset[tuple[int, int]] = frozenset(),
    ) -> None:
        """一次性布雷并预计算全部邻域数。

        候选集 = 全部真实格 − forbid，用 rng.sample 抽样（禁止 while 重抽）。

        Raises:
            RuntimeError: 本实例已布雷（只允许调用一次）。
            ValueError: mines < 0，或 mines > 候选格数。
                消息必须含：所需雷数、可用格数、forbid 规模。
        复杂度：抽样 O(k)，预计算 O(8N)。
        """
        raise NotImplementedError

    # ---------- 查询 ----------
    @property
    def mine_count(self) -> int:
        """已放置的雷数，布雷前为 0。"""
        raise NotImplementedError

    def is_mine(self, r: int, c: int) -> bool:
        """Raises: IndexError（不静默返回 False）。"""
        raise NotImplementedError

    def adjacent_at(self, r: int, c: int) -> int:
        """读预计算值，O(1)。Raises: IndexError。"""
        raise NotImplementedError

    def count_adjacent_raw(self, r: int, c: int) -> int:
        """现算 O(8)，带边界判断。仅供测试对照，产品代码禁用。"""
        raise NotImplementedError

    # ---------- 指纹与序列化 ----------
    def fingerprint(self) -> bytes:
        """雷位缓冲区 + 邻域数缓冲区拼接后的字节串（含边框）。

        长度 2*(rows+2)*(cols+2)。性质：同一盘面无论由 place_mines
        还是 from_hex 得到，指纹必须相同；不同盘面必须不同。
        同尺寸下可比，跨尺寸不可比。
        """
        raise NotImplementedError

    def to_hex(self) -> str:
        """真实格按行展开的 hex，长度 2*rows*cols，不含边框。"""
        raise NotImplementedError

    @classmethod
    def from_hex(cls, rows: int, cols: int, s: str) -> "Board":
        """to_hex 的逆操作；用于 examples/ 读写与往返测试。"""
        raise NotImplementedError

    def __repr__(self) -> str:
        """按行渲染：'#' 表雷，'0'-'8' 表邻域数，去边框。"""
        raise NotImplementedError