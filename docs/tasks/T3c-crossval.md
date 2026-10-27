# T3c 千局交叉验证

- 编号：T3c
- 前置：S3b 完成（80 项测试通过，tag v0.3-reveal）
- 对应验收项：A3
- 版本：v2（胜负用例改为确定性，新增两侧 delta 比对）

## 1. 任务

新建 `tests/test_against_reference.py`：在同一盘面上让 `Game` 与 `RefBoard`
执行相同的点击序列，逐次比对状态。

**不得修改 `src/` 下任何文件，不得修改 `tests/reference.py` 与 `tests/test_game.py`。**

## 2. 为什么需要独立随机源

点击序列必须与盘面生成解耦。若复用 `Game` 内部的 rng，调整点击策略会连带
改变盘面，出差异时无法判断是 `reveal` 错了还是参考实现错了。

## 3. 点击策略

```python
import random

def _pick(crng, g, revealed, flagged):
    """返回下一个要点击的格子；无可选时返回 None。"""
    frontier = [
        (r, c) for r in range(g.rows) for c in range(g.cols)
        if (r, c) not in revealed and (r, c) not in flagged
        and any((nr, nc) in revealed
                for nr, nc in _neighbors(r, c, g.rows, g.cols))
    ]
    everything = [
        (r, c) for r in range(g.rows) for c in range(g.cols)
        if (r, c) not in revealed and (r, c) not in flagged
    ]
    pool = frontier if crng.random() < 0.7 and frontier else everything
    return crng.choice(pool) if pool else None
```

`_neighbors` 自行实现（8 邻域 + 边界裁剪），不要 import `minesweeper.core`。

## 4. 一局比对的骨架（顺序不可改）

```python
def _run_game(seed, rows, cols, mines, max_clicks):
    """返回 (state, revealed_cells)，供整局确定性检查使用。"""
    g = Game(rows, cols, mines, seed=seed)
    crng = random.Random(seed * 7919 + 13)

    first = (rows // 2, cols // 2)
    delta = g.reveal(*first)                        # 被测动作
    ref = RefBoard(rows, cols, g.snapshot_mines())   # 取实际雷位（仅此时）
    ref_delta = ref.expand(*first)                   # 参考实现同一动作

    prev = set()
    assert set(g.revealed_cells) == set(ref.revealed_numbers())
    assert set(delta) == set(g.revealed_cells) - prev
    assert set(ref_delta) == set(delta)              # 两侧 delta 必须相等

    for _ in range(max_clicks):
        if g.state is not GameState.PLAYING:
            break
        cell = _pick(crng, g, set(g.revealed_cells), set())
        if cell is None:
            break

        prev = set(g.revealed_cells)
        delta = g.reveal(*cell)
        ref_delta = ref.expand(*cell)

        assert set(g.revealed_cells) == set(ref.revealed_numbers()), \
            f"seed={seed} cell={cell} 累计集合不一致"
        assert set(delta) == set(g.revealed_cells) - prev, \
            f"seed={seed} cell={cell} delta 与差集不一致"
        assert set(ref_delta) == set(delta), \
            f"seed={seed} cell={cell} 两侧 delta 不一致"

        rn = ref.revealed_numbers()
        for rc in g.revealed_cells:
            assert g.view(*rc).adjacent == rn[rc], \
                f"seed={seed} cell={cell} {rc} 邻域数不一致"

        if g.state is GameState.LOST:
            assert delta == [cell], f"seed={seed} 踩雷应只返回该格"
            break

    if g.state is GameState.WON:
        assert len(g.revealed_cells) == rows * cols - mines
    return g.state, g.revealed_cells
```

`assert delta == [cell]` 有意使用列表比较（踩雷只有一格，顺序无歧义），
额外验证"返回值恰为一格"。

## 5. 必须写的测试（共 6 条）

- `test_cross_validation_9x9_1000_games`：seed 0..999，9×9 / 10 雷，max_clicks=40
- `test_cross_validation_16x16_200_games`：seed 0..199，16×16 / 40 雷，max_clicks=60
- `test_crossval_zero_mines_win`：seed 0..4，`Game(9,9,0)`，首点 (4,4)
  → 81 格全开、`state` 为 WON、两侧 delta 与累计集合都相等
- `test_crossval_mine_click_lost`：seed 0..49，`Game(9,9,10)`，首点 (4,4) 后
  从 `snapshot_mines() - revealed_cells` 取一颗雷点开
  → LOST、`delta == [(r,c)]`、`ref` 的 delta 为 `{(r,c)}`、
  两侧累计集合仍相等、累计集合恰好增加该格
- `test_whole_run_deterministic`：同 seed 跑两次 `_run_game`，
  返回的 `(state, revealed_cells)` 完全相同
- `test_crossval_uses_only_public_api`：扫描本文件，断言不含
  `._board`、`._revealed`、`._flagged`

不写"在 N 局中至少出现一局 WON/LOST"这类依赖运气的用例。

## 6. 性能与如实记录

```bat
.venv\Scripts\python.exe -m pytest tests\test_against_reference.py -q --durations=3
```

把实际耗时与局数写进 `docs/perf.md`。若总耗时 > 60 秒，可降为 500 / 100 局，
但**必须在 docs/perf.md 与 README 写明实际局数**，不得声称 1000 局。

## 7. 允许修改

- 新建 `tests/test_against_reference.py`
- 不得修改：`src/**`、`tests/reference.py`、`tests/test_game.py`、
  `tests/test_board.py`、`tests/test_reference.py`、`tests/test_architecture.py`、
  `docs/**`、`.qoder/rules/**`、`pyproject.toml`

## 8. 明确不做

- 不测插旗相关语义（`toggle_flag` 未实现，`RefBoard` 无插旗概念）——S4b 另行立项
- 不给 `RefBoard` 加任何方法
- 不修改 `src/` 下的实现来"让交叉验证通过"

## 9. 交付方式（两轮）

第一轮：只输出文字，不改文件。
1. `_run_game` 的完整流程与每步断言理由；
2. 踩雷那一刻，`Game.revealed_cells` 与 `RefBoard.revealed_numbers().keys()`
   为什么仍然相等；
3. 你认为卡片有歧义或错误的地方，没有就写"无"。

第二轮（确认后）：实现并运行，粘贴完整输出与 `git diff --stat`。

## 10. 交付前自检

- `git diff --stat` 只有一个文件
- pytest 全绿，测试总数 80 → 86（新增 6 条）
- 单独跑本文件时记录了耗时，且 `docs/perf.md` 写入了实际局数与耗时