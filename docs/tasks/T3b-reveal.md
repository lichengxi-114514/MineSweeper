# T3b Game.reveal：延迟布雷与 BFS 展开

- 编号：T3b
- 前置：S2（Board）、S3a（tests/reference.py）完成
- 对应验收项：A2、A6、A7
- 版本：v2（删除无法复现的精确布局用例，改为性质断言 + 最小交叉验证）

## 1. 任务

实现 `src/minesweeper/core/game.py` 的四个成员：
`revealed_cells`、`view`、`reveal`、`snapshot_mines`；
并把 `core/__init__.py` 改为导出 `Game` / `GameState` / `CellView`。

`toggle_flag`、`chord`、`mines_left` **必须保持 `raise NotImplementedError`**（S4）。

## 2. 必须遵循

- `.qoder/rules/00-architecture.md`
- `.qoder/rules/10-testing.md`（严禁改断言迁就实现）
- `docs/decisions.md` D2 / D5 / D6 / D7 / D8 / D9 / D10

## 3. 实现约束

1. 布雷只在首次 `reveal` 发生，`forbid = Board.protected_cells(r, c, rows, cols)`。
   禁止在 `__init__` 里布雷。
2. `reveal` 的判定顺序（顺序本身是契约）：
   1) 越界 → `IndexError`（先于一切判断，D10）
   2) `state != PLAYING` → `[]`
   3) 已翻开 → `[]`
   4) 已插旗 → `[]`（D9）
   5) 尚未布雷 → `place_mines(...)`；**成功之后**才置 `_placed = True`
   6) 是雷 → 加入 `_revealed`、设 `_exploded` 与 `LOST`，返回 `[(r, c)]`，
      **不返回其他雷格**（那是 `view()` 的显示职责）
   7) 否则 `_flood(r, c)` 做 BFS
   8) `len(_revealed) == rows*cols - mines` → `WON`
3. `_flood` 用 `collections.deque` 迭代 BFS，**禁止递归**。
   （证据：`tests/test_reference.py::test_experiment_recursion_limit_40x40`）
4. `_flood` 的 docstring 必须写明不变量：
   "只有 adjacent_at==0 的格才传播；0 格的定义保证其 8 邻居均非雷，
   因此雷格不可能被入队，_flood 内无需判断邻居是否为雷。"
5. 已翻开格、已插旗格都不入队；入队前判一次，出队时再判一次已翻开。
6. `_flood` 是**唯一批准新增的私有方法**，其余成员不得增减。
7. `snapshot_mines()` 布雷前调用抛 `RuntimeError`，返回 `frozenset` 完整雷位。
   契约见骨架 docstring，不得修改其 docstring 的约束段。
8. `view().mine` 仅当 `state is LOST` 且该格有雷时为 True，其余一律 False。
9. 不得修改骨架里已实现的 `__init__` / `_in_bounds` / `_check_bounds`。
10. 单函数 ≤ 40 行；除 `rng.py` 外不得**产生**随机性（不得调用 `random` 模块函数）。

## 4. 允许修改

- `src/minesweeper/core/game.py`
- `src/minesweeper/core/__init__.py`
- 新建 `tests/test_game.py`

不得修改：`board.py`、`rng.py`、`tests/reference.py`、`tests/test_reference.py`、
`tests/test_board.py`、`tests/test_architecture.py`、`tests/test_smoke.py`、
`docs/**`、`.qoder/rules/**`、`pyproject.toml`、`examples/**`、`tools/**`。

## 5. 必须写的测试（tests/test_game.py）

> Game 的雷位由 `rng.sample` 决定，**测试无法指定布局**。
> 因此本文件只做"性质断言 + 与参考实现的最小交叉验证"；
> 精确布局的用例只存在于 `tests/test_reference.py`。
> 全量多次点击的等价性验证属 S3c，不在本阶段。

### 构造与校验
- `Game(9,9,72)` 成功；`Game(9,9,73)` 抛 `ValueError`，消息同时含 `72` 与 `73`
- `Game(2,2,0)` 成功；`Game(2,2,1)` 抛 `ValueError`
- `Game(3,3,0)` 成功；`Game(3,3,1)` 抛 `ValueError`
- `Game(0,5,0)`、`Game(5,0,0)`、`mines=-1` 抛 `ValueError`

### 首点安全（A2）
- 9×9 / 10 雷，三类位置（角、边上非角、内部）各约 1/3，共 10000 次
- 若总耗时 > 10 秒，可降为 1000 次，但**必须在 docs/perf.md 写明实际次数**
- 每次断言：`state is not LOST`；`view(r,c).revealed is True`；
  `view(r,c).mine is False`；首点 `protected_cells` 内所有格 `is_mine` 为 False

### 布雷与展开的性质
- 首次 `reveal` 后：`_board.mine_count == mines`
- 首点在 delta 中，`len(delta) >= 1`
- 首点非雷时：delta 中无雷格（`all(not _board.is_mine(x) for x in delta)`）
  ← 覆盖"0 格邻居必非雷"这一不变量
- 展开结构：除首点外，delta 中每个 `adjacent > 0` 的格，
  至少有一个 `adjacent == 0` 的已翻开邻居
- 已翻开格：`view(r,c).adjacent == _board.adjacent_at(r,c)`

### 重复操作
- 同一格连续点两次：第二次返回 `[]`，`revealed_cells` 不变
- 先点零格、再点另一非零格：两次 delta 交集为空

### 胜负（全部确定性，不依赖 seed）
- `Game(9,9,72)` + `reveal(4,4)` → delta **恰 9 格**，`state is WON`
  （保护 9 格、候选 72 格全为雷，非雷格就是那 3×3；`9 == 81-72` 立即胜利）
- `Game(2,2,0)` + `reveal(0,0)` → 4 格，WON
- `Game(1,3,0)` + `reveal(0,1)` → 3 格，WON
- 踩雷：先 `reveal` 一个安全格，再从 `snapshot_mines()` 取一个雷格 `reveal` 它
  → `state is LOST`；`exploded_cell` 为该格；返回列表恰为 `[该格]`；
  `len(revealed_cells)` 只比之前多 1
- LOST 后再 `reveal` 任一未翻开格 → `[]`

### 与参考实现的最小交叉验证（20 局，顺序不可颠倒）
```python
def test_cross_check_first_click_20_games():
    for seed in range(20):
        g = Game(9, 9, 10, seed=seed)
        delta = g.reveal(4, 4)                       # ① 被测动作
        layout = g.snapshot_mines()                  # ② 取实际雷位
        ref = RefBoard(9, 9, layout)                 # ③ 喂给参考实现
        ref.expand(4, 4)
        assert set(g.revealed_cells) == set(ref.revealed_numbers())
        assert set(delta) == set(g.revealed_cells)   # 首次点击时 delta == 累计
```

### 信息不泄露（A6 的信息面）
- 布雷后、`PLAYING` 时：全部格 `view().mine` 为 False
- `reveal` 之前：全部格 `revealed is False` / `adjacent == 0` / `mine is False`；
  `revealed_cells == frozenset()`
- LOST 后：所有雷格 `mine is True`，非雷格 `mine is False`
- `snapshot_mines()` 在布雷前调用 → `RuntimeError`

### 异常
- `reveal(-1,0)`、`reveal(9,0)`、`view(0,9)` 抛 `IndexError`
- LOST 后 `reveal(-1,0)` 仍抛 `IndexError`（D10）

## 6. 明确不做

- 不实现 `toggle_flag` / `chord` / `mines_left`（S4）
- 不做多次点击序列的全量比对（S3c）
- 不新增 `snapshot_mines` 之外的任何接口或私有方法
- 不让测试直接读 `game._board`（架构规则中的该例外已删除，
  需要雷位一律经 `snapshot_mines()`）
- 不做 GUI / CLI / 求解器 / 性能优化
- 不搜索 seed 去凑特定雷位布局

## 7. 交付方式（两轮）

**第一轮**：只输出文字，不改文件。
1. `reveal` 的完整判定顺序，对应 §3 第 2 条的 8 步，逐条说明实现位置；
2. BFS 的入队条件与去重策略，并说明"雷格为何永不入队"；
3. 你认为卡片有歧义或错误的地方，没有就写"无"。

**第二轮**（确认后）：实现并运行
`.venv\Scripts\python.exe -m pytest -q --tb=short`，
粘贴完整真实输出与 `git diff --stat`。不得摘要，不得只说"已通过"。

## 8. 交付前自检

```bat
.venv\Scripts\python.exe tools\check_skeleton.py
```

- `未实现 3`，且三条恰好是 `Game.toggle_flag` / `Game.chord` / `Game.mines_left`
- `空壳 0`
- `pytest` 全绿
- `git diff --stat` 只有三个文件