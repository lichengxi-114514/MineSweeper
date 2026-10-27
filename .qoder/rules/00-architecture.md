# 项目：扫雷（MineSweeper）—— 架构规则

## 分层（不可违反）
- `src/minesweeper/core/` 只允许 import 标准库。禁止 import tkinter、argparse、
  以及本项目任何 GUI / CLI 模块。
- `src/minesweeper/gui/` 与 `cli.py` 只调用 core 的公开接口，
  不得访问以下划线开头的属性。
- GUI 层不出现任何雷数计算、展开逻辑、胜负判定。若确实需要，先提出改 core 接口。

## core 公开接口（已冻结，改动前必须先问我）
    Game(rows, cols, mines, seed=None)
      .state                        -> GameState(PLAYING / WON / LOST)
      .view(r, c)                   -> CellView(revealed, flagged, adjacent, mine)
      .reveal(r, c)                 -> list[tuple[int, int]]   # 发生变化的格子
      .toggle_flag(r, c)            -> list[tuple[int, int]]
      .chord(r, c)                  -> list[tuple[int, int]]
      .mines_left                   -> int
      .exploded_cell                -> tuple[int, int] | None
      .revealed_cells               -> frozenset[tuple[int, int]]   # 累计已翻开
      .snapshot_mines()             -> frozenset[tuple[int, int]]   # 仅测试用，见 D7



## 硬性禁令
- `view()` 在 state != LOST 时，对未翻开格必须返回 `mine=False`（不得泄露雷位）。
- 禁止用递归做 0 区展开（大棋盘会 RecursionError）。
- 禁止模块级可变全局状态；随机性只能来自构造时传入的 seed。
- 除 `core/rng.py` 外，禁止**产生**随机性：不得调用 `random` 模块的任何函数，
  也不得 `from random import ...`。仅用于类型注解的 `import random` 允许。
- 随机性只能来自构造函数注入的 rng 实例（`rng.sample(...)` 等实例方法）。
- 所有坐标访问必须经过 `in_bounds()` / `neighbors()` 裁剪；
  禁止裸索引（Python 负索引会静默取到末格）。
- 邻域数字在布雷后一次性 O(8N) 预计算，不得在查询或渲染时重算；
  "现算"版本只允许出现在 `tests/reference.py`。
- 不得引入第三方运行时依赖（开发依赖仅 pytest）。
- 不得建 `utils.py` 之类的垃圾桶模块；按职责并入已有模块。
```markdown
- 已存在的接口骨架（`raise NotImplementedError` 的方法）视为契约：
  不得修改方法签名，不得改动 docstring 中 Args / Raises / 复杂度 / 禁止事项
  等描述契约的部分。认为契约有误时应先提出，不得自行修改。
- 骨架中已给出实现的辅助函数（如 `_off()`）不得重写。
- 每个任务完成后必须执行 `findstr /n "NotImplementedError" src` 自查；
  若本次任务目标不是补齐全部骨架，须说明剩余方法与原因。

## 代码风格
- 类型注解齐全；公开函数写 docstring（一句话说明契约即可）。
- 一个函数只做一件事；超过 40 行先拆再写。
- 禁止魔数：用 Enum 或具名常量表达"雷 / 旗 / 未翻开"。
- 单文件超过 300 行时提出拆分建议，不要自行大改结构。