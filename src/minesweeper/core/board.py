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

_NEIGHBOR_DELTAS: tuple[tuple[int, int], ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)


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

    def _precompute_adjacent(self) -> None:
        """遍历全部真实格，用 _offsets 累加邻域雷数写入 _adj。

        边框格天然为 0，无需 if 越界判断。由 place_mines 与 from_hex 共用。
        """
        for r in range(self.rows):
            base = (r + 1) * self._w
            for c in range(self.cols):
                off = base + c + 1
                self._adj[off] = sum(self._mine[off + d] for d in self._offsets)

    # ---------- 坐标与邻域 ----------
    def in_bounds(self, r: int, c: int) -> bool:
        """0-based 坐标是否落在真实格内。"""
        return 0 <= r < self.rows and 0 <= c < self.cols

    def neighbors(self, r: int, c: int) -> Iterator[tuple[int, int]]:
        """生成已裁剪的合法邻居（0-based），绝不返回边框坐标。

        Raises:
            IndexError: (r, c) 本身越界。与 is_mine/adjacent_at 保持一致，
                不静默返回空迭代器（那会掩盖调用点错误）。

        注意：生成器只能迭代一次。热路径请直接迭代 self._offsets。
        """
        if not self.in_bounds(r, c):
            raise IndexError(f"({r}, {c}) 越界：棋盘 {self.rows}x{self.cols}")
        deltas = _NEIGHBOR_DELTAS
        in_bounds = self.in_bounds
        return ((r + dr, c + dc) for dr, dc in deltas if in_bounds(r + dr, c + dc))

    # ---------- 首点保护（D3 / D6）----------
    @staticmethod
    def protected_cells(r: int, c: int, rows: int, cols: int) -> frozenset[tuple[int, int]]:
        """首点 (r,c) 的保护集 = 自身 ∪ 8 邻域（越界裁剪）。"""
        cells: set[tuple[int, int]] = {(r, c)}
        for dr, dc in _NEIGHBOR_DELTAS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                cells.add((nr, nc))
        return frozenset(cells)

    @staticmethod
    def protected_max(rows: int, cols: int) -> int:
        """所有可能首点中保护集的最大值 = min(rows,3) * min(cols,3)。"""
        return min(rows, 3) * min(cols, 3)

    @staticmethod
    def max_mines_at(r: int, c: int, rows: int, cols: int) -> int:
        """以 (r,c) 为首点时的单格上限 = rows*cols - len(protected_cells)。

        Raises:
            IndexError: (r,c) 越界。
        """
        if not (0 <= r < rows and 0 <= c < cols):
            raise IndexError(f"({r}, {c}) 越界：棋盘 {rows}x{cols}")
        return rows * cols - len(Board.protected_cells(r, c, rows, cols))

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
        if self._placed:
            raise RuntimeError("本实例已布雷，不可重复调用")
        if mines < 0:
            raise ValueError(f"雷数不能为负，收到 {mines}")
        candidates = [
            self._off(r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in forbid
        ]
        if len(candidates) < mines:
            raise ValueError(
                f"候选不足：需要 {mines} 雷，可用 {len(candidates)} 格，"
                f"forbid {len(forbid)} 格"
            )
        for off in rng.sample(candidates, mines):
            self._mine[off] = MINE
        self._precompute_adjacent()
        self._mine_count = mines
        self._placed = True

    # ---------- 查询 ----------
    @property
    def mine_count(self) -> int:
        """已放置的雷数，布雷前为 0。"""
        return self._mine_count

    def is_mine(self, r: int, c: int) -> bool:
        """Raises: IndexError（不静默返回 False）。"""
        if not self.in_bounds(r, c):
            raise IndexError(f"({r}, {c}) 越界：棋盘 {self.rows}x{self.cols}")
        return self._mine[self._off(r, c)] == MINE

    def adjacent_at(self, r: int, c: int) -> int:
        """读预计算值，O(1)。Raises: IndexError。
        雷格也有邻域数，不强制为 0。"""
        if not self.in_bounds(r, c):
            raise IndexError(f"({r}, {c}) 越界：棋盘 {self.rows}x{self.cols}")
        return self._adj[self._off(r, c)]

    def count_adjacent_raw(self, r: int, c: int) -> int:
        """现算 O(8)，带边界判断。仅供测试对照，产品代码禁用。"""
        if not self.in_bounds(r, c):
            raise IndexError(f"({r}, {c}) 越界：棋盘 {self.rows}x{self.cols}")
        count = 0
        for dr, dc in _NEIGHBOR_DELTAS:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc) and self._mine[self._off(nr, nc)] == MINE:
                count += 1
        return count

    # ---------- 指纹与序列化 ----------
    def fingerprint(self) -> bytes:
        """雷位缓冲区 + 邻域数缓冲区拼接后的字节串（含边框）。

        长度 2*(rows+2)*(cols+2)。性质：同一盘面无论由 place_mines
        还是 from_hex 得到，指纹必须相同；不同盘面必须不同。
        同尺寸下可比，跨尺寸不可比。
        """
        return bytes(self._mine) + bytes(self._adj)

    def to_hex(self) -> str:
        """真实格按行展开的 hex，长度 2*rows*cols，不含边框。

        编码：每格 1 字节 = mine*16 + adj，小写 hex、无分隔符。
        """
        buf = bytearray(self.rows * self.cols)
        idx = 0
        for r in range(self.rows):
            base = (r + 1) * self._w
            for c in range(self.cols):
                off = base + c + 1
                buf[idx] = self._mine[off] * 16 + self._adj[off]
                idx += 1
        return buf.hex()

    @classmethod
    def from_hex(cls, rows: int, cols: int, s: str) -> "Board":
        """to_hex 的逆操作；用于 examples/ 读写与往返测试。

        校验（缺一抛 ValueError，消息含原因与首个出错坐标）：
        长度 / hex 字符 / 高 4 位<=1 / 低 4 位<=8 / 由雷位重算 adj 一致。
        通过后置 _placed=True、_mine_count=雷位数。
        """
        expected = 2 * rows * cols
        if len(s) != expected:
            raise ValueError(
                f"hex 长度错误：期望 {expected}，收到 {len(s)}"
            )
        try:
            data = bytes.fromhex(s)
        except ValueError:
            raise ValueError("hex 字符错误：含非十六进制字符")
        board = cls(rows, cols)
        provided_adj = bytearray(rows * cols)
        for idx, b in enumerate(data):
            r, c = divmod(idx, cols)
            mine_hi = b >> 4
            adj_lo = b & 0xF
            if mine_hi > 1:
                raise ValueError(
                    f"格 ({r},{c}) 高 4 位 = {mine_hi}，应 <= 1"
                )
            if adj_lo > 8:
                raise ValueError(
                    f"格 ({r},{c}) 低 4 位 = {adj_lo}，应 <= 8"
                )
            off = board._off(r, c)
            board._mine[off] = mine_hi
            provided_adj[idx] = adj_lo
        board._precompute_adjacent()
        for idx in range(len(data)):
            r, c = divmod(idx, cols)
            off = board._off(r, c)
            if board._adj[off] != provided_adj[idx]:
                raise ValueError(
                    f"格 ({r},{c}) adj = {provided_adj[idx]}，"
                    f"由雷位重算 = {board._adj[off]}"
                )
        board._mine_count = sum(board._mine)
        board._placed = True
        return board

    def __repr__(self) -> str:
        """按行渲染：'#' 表雷，'0'-'8' 表邻域数，去边框。"""
        lines: list[str] = []
        for r in range(self.rows):
            row_chars: list[str] = []
            for c in range(self.cols):
                off = self._off(r, c)
                if self._mine[off]:
                    row_chars.append('#')
                else:
                    row_chars.append(str(self._adj[off]))
            lines.append(''.join(row_chars))
        return '\n'.join(lines)
