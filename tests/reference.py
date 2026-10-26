# tests/reference.py
"""笨但明显正确的展开引擎，仅用于测试对照。

独立性约束：
- 不 import minesweeper.core 或任何本项目模块
- 允许递归、允许每次现算、允许 O(N²)
- 全仓库只有本文件允许用递归做 flood fill
"""
from __future__ import annotations


class RefBoard:
    def __init__(
        self,
        rows: int,
        cols: int,
        mine_cells: frozenset[tuple[int, int]],
    ) -> None:
        """雷位由外部给定；本类不布雷、不接触随机数。

        Raises:
            ValueError: rows/cols < 1；或 mine_cells 含越界坐标
                （消息含该坐标与棋盘尺寸）。
        """
        if rows < 1 or cols < 1:
            raise ValueError(f"棋盘尺寸必须 >= 1，收到 {rows}x{cols}")
        for r, c in mine_cells:
            if not (0 <= r < rows and 0 <= c < cols):
                raise ValueError(
                    f"雷位 ({r},{c}) 越界：棋盘 {rows}x{cols}"
                )
        self.rows = rows
        self.cols = cols
        self._mines: set[tuple[int, int]] = set(mine_cells)
        self._revealed: set[tuple[int, int]] = set()

    def in_bounds(self, r: int, c: int) -> bool:
        """0-based 坐标是否落在盘内。"""
        return 0 <= r < self.rows and 0 <= c < self.cols

    def adjacent(self, r: int, c: int) -> int:
        """现算 (r,c) 八邻域中的雷数，逐格遍历，O(8)。

        Raises:
            IndexError: (r,c) 越界。
        """
        if not self.in_bounds(r, c):
            raise IndexError(f"({r},{c}) 越界：棋盘 {self.rows}x{self.cols}")
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc) and (nr, nc) in self._mines:
                    count += 1
        return count

    def expand(self, r: int, c: int) -> set[tuple[int, int]]:
        """从 (r,c) 展开，返回本次新翻开的格子集合（含 (r,c) 自身）。

        Raises:
            IndexError: (r,c) 越界。
        """
        if not self.in_bounds(r, c):
            raise IndexError(f"({r},{c}) 越界：棋盘 {self.rows}x{self.cols}")
        if (r, c) in self._revealed:
            return set()
        before = set(self._revealed)
        self._flood(r, c)
        return self._revealed - before

    def _flood(self, r: int, c: int) -> None:
        """递归 flood fill：翻开 (r,c)，若 adj==0 则递归展开 8 邻居。"""
        if (r, c) in self._revealed:
            return
        self._revealed.add((r, c))
        if (r, c) in self._mines:
            return
        if self.adjacent(r, c) == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if self.in_bounds(nr, nc):
                        self._flood(nr, nc)

    def revealed_numbers(self) -> dict[tuple[int, int], int]:
        """已翻开格 -> 其邻域数。未翻开的格子不得出现。"""
        return {(r, c): self.adjacent(r, c) for (r, c) in self._revealed}
