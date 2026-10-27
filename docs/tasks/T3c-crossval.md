# T3c 千局交叉验证

- 编号：T3c
- 前置：S3b 完成（80 项测试通过，tag v0.3-reveal）
- 对应验收项：A3
- 版本：v1

## 1. 任务

新建 `tests/test_against_reference.py`：在同一盘面上让 `Game` 与 `RefBoard`
执行相同的点击序列，逐次比对状态。

**不得修改 `src/` 下任何文件，不得修改 `tests/reference.py` 与 `tests/test_game.py`。**

## 2. 为什么需要独立随机源

点击序列必须与盘面生成解耦。若复用 `Game` 内部的 rng，调整点击策略会连带
改变盘面，出差异时无法判断是 `reveal` 错了还是参考实现错了。

## 3. 点击策略（必须完全按此实现）

```python
import random

def _pick(crng, g, revealed, flagged):
    """返回下一个要点击的格子。revealed/flagged 为当前集合。"""
    candidates_frontier = [
        (r, c) for r in range(g.rows) for c in range(g.cols)
        if (r, c) not in revealed and (r, c) not in flagged
        and any((nr, nc) in revealed for nr, nc in _neighbors(r, c, g.rows, g.cols))
    ]
    everything = [
        (r, c) for r in range(g.rows) for c in range(g.cols)
        if (r, c) not in revealed and (r, c) not in flagged
    ]
    pool = candidates_frontier if crng.random() < 0.7 and candidates_frontier else everything
    return crng.choice(pool) if pool else None
```

`_neighbors` 自行实现（8 邻域 + 边界裁剪），不要 import `minesweeper.core`。

## 4. 一局比对的骨架（顺序不可改）

```python
def _run_game(seed, rows, cols, mines, max_clicks):
    g = Game(rows, cols, mines, seed=seed)
    crng = random.Random(seed * 7919 + 13)

    first = (rows // 2, cols // 2)
    delta = g.reveal(*first)                      # ① 被测动作
    ref = RefBoard(rows, cols, g.snapshot_mines())  # ② 取实际雷位（仅此时）
    ref.expand(*first)                            # ③ 参考实现执行同一动作

    prev = set()
    assert set(g.revealed_cells) == set(ref.revealed_numbers())
    assert set(delta) == set(g.revealed_cells) - prev

    for _ in range(max_clicks):
        if g.state is not GameState.PLAYING:
            break
        cell = _pick(crng, g, set(g.revealed_cells), set())
        if cell is None:
            break
        prev = set(g.revealed_cells)
        delta = g.reveal(*cell)
        ref.expand(*cell)

        assert set(g.revealed_cells) == set(ref.revealed_numbers()), \
            f"seed={seed} cell={cell} 累计集合不一致"
        assert set(delta) == set(g.revealed_cells) - prev, \
            f"seed={seed} cell={cell} delta 与差集不一致"

        rn = ref.revealed_numbers()
        for rc in g.revealed_cells:
            assert g.view(*rc).adjacent == rn[rc], \
                f"seed={seed} cell={cell} {rc} 邻域数不一致"

        if g.state is GameState.LOST:
            assert delta == [cell], f"seed={seed} 踩雷应只返回该格"
            break

    if g.state is GameState.WON:
        assert len(g.revealed_cells) == rows * cols - mines
    return g.state
```

## 5. 必须写的测试

- `test_cross_validation_9x9_1000_games`：seed 0..999，9×9 / 10 雷，max_clicks=40
- `test_cross_validation_16x16_200_games`：seed 0..199，16×16 / 40 雷，max_clicks=60
- `test_both_outcomes_observed`：上面覆盖的局中，至少各出现一局 WON 与一局 LOST
  （若未出现，说明点击策略有问题，不是放宽断言的理由）
- `test_click_sequence_deterministic`：同一 seed 调用两次 `_pick` 序列得到相同结果
- `test_no_src_import_in_test`：断言本文件不含 `import minesweeper.core.game` 之外
  的内部访问（允许 import Game/GameState/GameRef 的公开名字）

## 6. 性能与如实记录

先单独跑 9×9 那 1000 局，记录耗时：

```bat
.venv\Scripts\python.exe -m pytest tests\test_against_reference.py -q --durations=3
```

把实际耗时写进 `docs/perf.md`。若总耗时 > 60 秒，可降为 500 局，
但**必须在 docs/perf.md 与 README 中写明实际局数**，不得声称 1000 局。

## 7. 允许修改

- 新建 `tests/test_against_reference.py`
- 不得修改：`src/**`、`tests/reference.py`、`tests/test_game.py`、
  `tests/test_board.py`、`tests/test_reference.py`、`tests/test_architecture.py`、
  `docs/**`、`.qoder/rules/**`、`pyproject.toml`

## 8. 明确不做

- 不测插旗相关语义（Game.toggle_flag 未实现，RefBoard 无插旗概念）——S4b 另行立项
- 不给 RefBoard 加任何方法
- 不修改 src/ 下的实现来"让交叉验证通过"

## 9. 交付方式（两轮）

第一轮：只输出文字，不改文件。给出
1. `_run_game` 的完整流程与你对每一步断言理由的说明；
2. 踩雷那一刻，`Game.revealed_cells` 与 `RefBoard.revealed_numbers().keys()`
   为什么仍然应当相等；
3. 你认为卡片有歧义或错误的地方，没有就写"无"。

第二轮（确认后）：实现并运行，粘贴完整输出与 `git diff --stat`。

## 10. 交付前自检

- `git diff --stat` 只有一个文件
- pytest 全绿，测试总数增加 5 条
- `docs/perf.md` 已记录实际耗时与局数