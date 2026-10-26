# src/minesweeper/core/game.py
"""游戏状态机：延迟布雷、翻开、胜负判定。

不变量（违反即为 bug）
----------------------
1. 构造时**不布雷**。首次 reveal 才调用 Board.place_mines，
   forbid = 首点的 protected_cells。这条保证 A2（首点安全）。
2. 未布雷时 adjacent_at 全部为 0，因此"未布雷就查询"不会泄露信息，
   但也绝不能据此判定盘面。
3. view() 在 state != LOST 时，对任何格都返回 mine=False（不泄露雷位）。
4. reveal 返回的是**本次新增**翻开的格子（delta），供 GUI 增量重绘；
   已翻开的格再次点击返回空列表，不报错。

设计依据见 docs/decisions.md D2/D5/D6/D7/D8。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum

from .board import Board
from .rng import make_rng


class GameState(Enum):
    """对局状态。"""

    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass(frozen=True)
class CellView:
    """单个格子对玩家可见的信息。不含任何未公开的雷位。"""

    revealed: bool
    flagged: bool
    adjacent: int
    mine: bool


class Game:
    """一局扫雷。一次性使用：结束后需新建实例重开。"""

    rows: int
    cols: int
    mines: int

    def __init__(self, rows: int, cols: int, mines: int,
                 seed: int | None = None) -> None:
        """创建未布雷的对局。

        构造期校验（D6=B）：
            0 <= mines <= rows*cols - Board.protected_max(rows, cols)
        由此保证**任何首点**都能开局，UI 无需预检。

        Raises:
            ValueError: rows/cols < 1；或 mines 不在上述区间。
                消息必须同时含：允许上界、实际传入的 mines、棋盘尺寸。
        """
        if rows < 1 or cols < 1:
            raise ValueError(f"棋盘尺寸必须 >= 1，收到 {rows}x{cols}")
        upper = rows * cols - Board.protected_max(rows, cols)
        if not 0 <= mines <= upper:
            raise ValueError(
                f"{rows}x{cols} 的雷数必须在 0..{upper} 之间，收到 {mines}"
            )
        self.rows, self.cols, self.mines = rows, cols, mines
        self._seed = seed
        self._rng = make_rng(seed)
        self._board = Board(rows, cols)
        self._revealed: set[tuple[int, int]] = set()
        self._flagged: set[tuple[int, int]] = set()
        self._state = GameState.PLAYING
        self._exploded: tuple[int, int] | None = None
        self._placed = False

    # ---------- 内部 ----------
    def _in_bounds(self, r: int, c: int) -> bool:
        """唯一越界判断出口。"""
        return 0 <= r < self.rows and 0 <= c < self.cols

    def _check_bounds(self, r: int, c: int) -> None:
        """越界即抛。所有公开方法的第一行都调用它。"""
        if not self._in_bounds(r, c):
            raise IndexError(f"坐标越界: ({r}, {c})，棋盘 {self.rows}x{self.cols}")

    # ---------- 状态查询 ----------
    @property
    def state(self) -> GameState:
        """当前对局状态。"""
        return self._state

    @property
    def exploded_cell(self) -> tuple[int, int] | None:
        """被踩中的雷格；未踩雷时为 None。GUI 用于标红。"""
        return self._exploded

    @property
    def revealed_cells(self) -> frozenset[tuple[int, int]]:
        """累计已翻开的格子（跨多次 reveal，不只是最近一次）。

        用途：S3c 与 RefBoard.revealed_numbers().keys() 逐次比对。
        """
        raise NotImplementedError

    def view(self, r: int, c: int) -> CellView:
        """该格对玩家可见的信息。

        契约：
            - revealed = 该格在 _revealed 中
            - flagged  = 该格在 _flagged 中
            - adjacent = 已翻开时返回真实邻域数；未翻开时返回 0
            - mine     = 仅当 state 为 LOST 且该格有雷时为 True；
                         其余情况一律 False（含已翻开的非雷格、未布雷时）

        Raises:
            IndexError: 坐标越界（先于任何状态判断）。
        """
        raise NotImplementedError

    # ---------- 核心操作（S3b 实现）----------
    def reveal(self, r: int, c: int) -> list[tuple[int, int]]:
        """翻开 (r,c)，返回本次新增翻开的格子列表（delta，顺序不限）。

        执行顺序（必须逐条核对，顺序本身是契约）：
            1. 越界 -> IndexError（先于一切判断）
            2. state != PLAYING -> 返回 []
            3. 该格已翻开 -> 返回 []
            4. 该格已插旗 -> 返回 []（A6）
            5. 尚未布雷 -> 布雷：
                   forbid = Board.protected_cells(r, c, rows, cols)
                   self._board.place_mines(self._rng, self.mines, forbid)
                   self._placed = True
            6. 该格是雷 -> _revealed 加入该格、设 _exploded 与 LOST，
               返回 [(r,c)]。**不得返回其他雷格**（那是 view 的职责）
            7. 否则 BFS 展开：
               - 用 collections.deque；**禁止递归**
               - 每格加入 _revealed 与返回值
               - 仅当 adjacent_at == 0 时把其 8 邻居入队
               - 已翻开/已插旗的格不入队
            8. 展开后若 len(_revealed) == rows*cols - mines，置 WON

        Raises:
            IndexError: 坐标越界。
        """
        raise NotImplementedError

    # ---------- 插旗与和弦（S4 实现，本轮保持未实现）----------
    def toggle_flag(self, r: int, c: int) -> list[tuple[int, int]]:
        """插旗/取消插旗，返回变化的格子列表。

        Raises:
            NotImplementedError: 本阶段未实现（S4）。
        """
        raise NotImplementedError

    def chord(self, r: int, c: int) -> list[tuple[int, int]]:
        """双击和弦展开，返回变化的格子列表。

        Raises:
            NotImplementedError: 本阶段未实现（S4）。
        """
        raise NotImplementedError

    @property
    def mines_left(self) -> int:
        """剩余雷数估计 = mines - 已插旗数（可为负，UI 自行处理）。

        Raises:
            NotImplementedError: 本阶段未实现（S4）。
        """
        raise NotImplementedError