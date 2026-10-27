# T4 toggle_flag / chord / mines_left

- 编号：T4
- 前置：S3c 完成（86 项测试通过）
- 对应验收项：A5、A6、A7 的插旗相关部分
- 版本：v1

## 1. 任务

填入 `src/minesweeper/core/game.py` 中三个现成的占位方法：
`toggle_flag`、`chord`、`mines_left`。

本任务完成后 `tools/check_skeleton.py` 应显示"未实现 0"。

## 2. 必须遵循

- `.qoder/rules/00-architecture.md`、`10-testing.md`
- `docs/decisions.md` 的 D9、D13、D14、D15、D16
- 不得修改 `__init__` / `_in_bounds` / `_check_bounds` / `reveal` / `_flood` /
  `view` / `revealed_cells` / `snapshot_mines` 的任何已实现逻辑
- 不得修改 `_flagged` 的类型（保持 `set[tuple[int, int]]`）

## 3. 实现约束

### toggle_flag(r, c) -> list[tuple[int, int]]

1. 越界 -> `IndexError`（先于一切判断）
2. `state != PLAYING` -> `[]`
3. 该格已翻开 -> `[]`（A6：已翻开格不可插旗）
4. 否则在 `_flagged` 中切换：不在则加入、在则移除
5. 返回 `[(r, c)]`（变化格）

不限制旗数（D13）。插旗不修改 `_revealed`、不触发布雷、不影响 `state`。

### chord(r, c) -> list[tuple[int, int]]

1. 越界 -> `IndexError`
2. `state != PLAYING` -> `[]`
3. 未翻开 -> `[]`
4. `adjacent_at(r, c) == 0` -> `[]`
5. 统计 8 邻域中 `_flagged` 的数量 `nf`
6. `nf != adjacent_at(r, c)` -> `[]`，且 **`_revealed` / `_flagged` / `_state`
   三者均不得改变**（原子性，A5）
7. 对 8 邻域中"未翻开且未插旗"的格逐一 `self.reveal(nr, nc)`，聚合 delta
8. 若中途 `state` 变为 LOST，停止循环并返回已聚合的 delta
9. 返回聚合后的 delta（顺序不限，不得包含重复格）

### mines_left -> int

- 返回 `self.mines - len(self._flagged)`，可为负。不受 `state` 影响。

## 4. 允许修改

- `src/minesweeper/core/game.py`（仅三个方法体）
- 补充 `tests/test_game.py` 中与插旗 / chord 有关的用例

不得修改：`board.py`、`rng.py`、`__init__.py`、`tests/reference.py`、
`tests/test_against_reference.py`、`tests/test_board.py`、
`tests/test_reference.py`、`tests/test_architecture.py`、`docs/**`、
`README.md`、`.qoder/rules/**`、`pyproject.toml`

## 5. 必须写的测试（全部确定性，不依赖运气）

### 插旗基础

- 未布雷即可插旗：`Game(9,9,10)` 构造后 `toggle_flag(0,0)` 返回 `[(0,0)]`，
  `view(0,0).flagged is True`，`mines_left == 9`
- 再次调用返回 `[(0,0)]` 且 `flagged is False`，`mines_left == 10`
- 已翻开格：先 `reveal` 一格，再 `toggle_flag` 该格 -> `[]`，`flagged` 仍为 False
- 旗数超雷数：`Game(9,9,1)` 连插 5 旗 -> 无异常，`mines_left == -4`
- 越界 -> `IndexError`；LOST 后 -> `[]`

### D9 与 D16 组合（确定性，最有信息量）

- `Game(9,9,0)`：`toggle_flag(4,4)` -> `reveal(0,0)`
  断言 `len(revealed_cells) == 80`、`(4,4) not in revealed_cells`、
  `state is PLAYING`（未通关）、`mines_left == -1`
- 随后 `toggle_flag(4,4)` 撤旗、`reveal(4,4)` -> `len(revealed_cells) == 81`、
  `state is WON`

### chord

- `test_chord_on_unrevealed_returns_empty`：未翻开格 -> `[]`
- `test_chord_on_zero_cell_returns_empty`：用 `snapshot_mines()` 找一个已翻开
  且 `adjacent == 0` 的格 -> `[]`
- `test_chord_flag_mismatch_is_atomic`：用 `snapshot_mines()` 找已翻开且
  `adjacent >= 2` 的格，只插 1 面旗（数不匹配）；记录调用前的
  `revealed_cells` 与 flagged 集合，调用 chord -> `[]`，且两个集合与 `state`
  全部不变
- `test_chord_correct_flags_reveals_neighbors`：用 `snapshot_mines()` 找出某已翻开格
  的全部雷邻居并逐一插旗，然后 chord -> 返回集合恰好等于
  "该格 8 邻域中未翻开、未插旗、非雷"的格
- `test_chord_wrong_flag_hits_mine`：找已翻开且 `adjacent == 1` 的格，
  把旗插在非雷邻居上（数匹配但位置错），chord -> `state is LOST`、
  `exploded_cell` 是那颗雷、delta 含该雷格
- `test_chord_delta_has_no_duplicates`：正确 chord 后断言
  `len(delta) == len(set(delta))`

### 信息面

- 插旗不泄露雷位：非 LOST 时对所有格断言 `view(r,c).mine is False`

## 6. 明确不做

- 不做自动 chord（点击数字格自动展开）、不做长按、不做问号旗
- 不做 UI
- 不给 `RefBoard` 加插旗概念（旗相关的差分验证不在本阶段）

## 7. 交付方式（两轮）

**第一轮**：只输出文字，不改文件。给出

1. `chord` 的判定顺序，并说明第 5、6 步为何必须在第 7 步之前；
2. `test_chord_flag_mismatch_is_atomic` 你会如何构造那个 `adjacent >= 2`
   的已翻开格（不得写死坐标），以及为什么不写死；
3. 你认为卡片或决策记录有歧义的地方，没有就写"无"。

**第二轮**（确认后）：实现并运行，粘贴完整输出与 `git diff --stat`。

## 8. 交付前自检

- `tools/check_skeleton.py` -> `未实现 0，空壳 0`
- `git diff --stat` 只有 `game.py` 与 `tests/test_game.py`
- pytest 全绿，总数 86 -> 约 97
- 未修改 `reveal` / `_flood` 的任何一行