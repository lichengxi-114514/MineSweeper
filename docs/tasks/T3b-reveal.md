# T3b Game.reveal：延迟布雷与 BFS 展开

- 编号：T3b
- 前置：S2（Board）、S3a（tests/reference.py）完成
- 对应验收项：A2、A6、A7
- 版本：v1

## 1. 任务

实现 `src/minesweeper/core/game.py` 中以下五个成员：
`revealed_cells`、`view`、`reveal`，以及把 `core/__init__.py` 改为导出
`Game` / `GameState` / `CellView`。

**`toggle_flag`、`chord`、`mines_left` 保持 `NotImplementedError`**，属 S4。

## 2. 必须遵循

- `.qoder/rules/00-architecture.md`
- `docs/decisions.md` D2/D5/D6/D7/D8/D9/D10
- `__init__` 与 `_in_bounds` / `_check_bounds` 已实现，**不得改写**

## 3. 实现约束

1. 布雷只在首次 `reveal` 发生，`forbid = Board.protected_cells(r, c, rows, cols)`。
   禁止在 `__init__` 里布雷。
2. 展开用 `collections.deque` 迭代 BFS。**禁止递归**
   （证据：40×40 全 0 盘面在递归实现下触发 RecursionError，见
   `tests/test_reference.py::test_experiment_recursion_limit_40x40`）。
3. `reveal` 返回 delta（本次新增），已翻开格返回 `[]`。
4. 踩雷时 `reveal` 只返回被踩中的那一格，`_revealed` 只加入那一格。
5. 插旗格不参与自动展开（D9），也不可被直接翻开。
6. `view().mine` 只在 `state is LOST` 时为真，其余一律 False。
7. 胜负：展开后 `len(_revealed) == rows*cols - mines` 即 WON。
8. 单函数 ≤ 40 行；`reveal` 允许把 BFS 抽成私有方法 `_flood`，这是
   **唯一批准新增的成员**。
9. 除 `rng.py` 外不得 `import random`。`game.py` 中不得出现 `random` 字样
   的 import（`make_rng` 已封装）。

## 4. 允许修改

- `src/minesweeper/core/game.py`
- `src/minesweeper/core/__init__.py`
- 新建 `tests/test_game.py`
- 不得修改：`src/minesweeper/core/board.py`、`rng.py`、`tests/reference.py`、
  `tests/test_reference.py`、`tests/test_board.py`、`docs/**`、
  `.qoder/rules/**`、`pyproject.toml`、`examples/**`

## 5. 必须写的测试（tests/test_game.py）

构造与校验
- `Game(9,9,72)` 成功；`Game(9,9,73)` 抛 ValueError，消息含 72 与 73
- `Game(2,2,0)` 成功；`Game(2,2,1)` 抛 ValueError
- `Game(3,3,0)` 成功；`Game(3,3,1)` 抛 ValueError
- `Game(0,5,...)`、`Game(5,0,...)` 抛 ValueError；`mines=-1` 抛 ValueError

首点安全（A2）
- 10000 次首点：三类位置（角/边上/内部）各约 3333 次，
  尺寸 9×9、mines=10，每次新建 Game（seed 递增）后 `reveal` 首点，
  断言 `state is not LOST` 且 `view(r,c).revealed is True` 且 `view(r,c).mine is False`
- 若该用例总耗时 > 10 秒，改为 1000 次，并在 `docs/perf.md` 如实记录
  "抽样 1000 次"，不得声称 10000 次

布雷正确性
- 首次 reveal 后 `game._board.mine_count == game.mines`
- 首点的 `protected_cells` 内所有格 `mine` 均为 False（100 次不同 seed）
- 对全部已翻开格，`view(r,c).adjacent == game._board.adjacent_at(r,c)`

展开语义
- 用例 A（4×4、第 1 列整列雷、点 (0,3)）：`reveal` 返回 8 格，
  集合等于 `tests/reference.py` §6 的期望集合
- 用例 B（同上、点 (1,0)）：返回恰好 1 格 `[(1,0)]`
- 用例 C（1×9、雷在 (0,4)、点 (0,0)）：返回 4 格
- 重复点同一格：第二次返回 `[]`，`revealed_cells` 不变
- 点已翻开的数字格：返回 `[]`

胜负（A7）
- 1×3、mines=1、首点 (0,0)（受保护集为前两格）：
  再翻开剩余非雷格后 → WON，且此时 `revealed_cells` 含全部 2 个非雷格
- 踩雷：`reveal` 后 `state is LOST`、`exploded_cell == 该格`、
  `len(revealed_cells) == 1`、`view(该格).mine is True`
- LOST 后再次 `reveal` 其他格：返回 `[]`，状态不变

不泄露（A6 的信息面）
- 布雷后、未踩雷时，对所有格断言 `view(r,c).mine is False`
- 未布雷时（任何 reveal 之前）：所有格 `revealed is False`、`adjacent == 0`、
  `mine is False`，`revealed_cells == frozenset()`

异常
- `reveal(-1,0)`、`reveal(rows,0)`、`view(0,cols)` 抛 IndexError
- LOST 之后 `reveal(-1,0)` 仍抛 IndexError（D10）

## 6. 明确不做

- 不实现 `toggle_flag` / `chord` / `mines_left`（S4）
- 不与 `RefBoard` 做逐次比对（那是 S3c，需要独立任务）
- 不做 GUI、CLI、求解器
- 不做性能优化（BFS 已足够；不预计算任何东西）

## 7. 交付方式（两轮）

第一轮：只输出文字，不改文件。给出
1. `reveal` 的完整判定顺序（对应 §3 的 8 步，逐条说明你的实现位置）；
2. BFS 的入队条件与去重策略（在哪里判已翻开、在哪里判已插旗）；
3. 用例 A 的展开结果集合，与 `tests/reference.py` §6 对照；
4. 你认为卡片有歧义或错误的地方，没有就写"无"。

第二轮（确认后）：实现并运行
`.venv\Scripts\python.exe -m pytest -q --tb=short`，粘贴完整输出与 `git diff --stat`。
不得摘要，不得只说"已通过"。

## 8. 交付前自检

- `findstr /n "NotImplementedError" src\minesweeper\core\game.py` 恰好 3 处
  （`toggle_flag` / `chord` / `mines_left`）
- `src/` 下除 `game.py` 与 `__init__.py` 无其他改动
- pytest 全绿