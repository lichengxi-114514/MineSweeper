# T3a 参考实现 tests/reference.py

- 编号：T3a
- 前置：S2 完成（Board 实现、31 项测试通过、tag `v0.2-board`）
- 对应验收项：A3
- 版本：v2（用例经复核后替换，过程见 docs/ai-log.md 案例 2）

## 1. 任务

新建 `tests/reference.py`：一个笨但明显正确的展开引擎，仅用于测试对照。
本任务不实现 Game，不改动 `src/` 下任何文件。

## 2. 为什么需要它

`reveal` 的正式实现是 BFS + 预计算邻域数。它有 bug 时，用同一段代码算不出正确期望值，
测试会变成"用错误代码证明错误代码正确"。
参考实现的价值全在独立路径：不同的算法、不同的数据结构、不同的遍历方式。
因此它必须牺牲性能换取直觉上的正确性。

## 3. 独立性约束（违反即失败）

- 不得 import `minesweeper.core` 或任何本项目模块，只允许标准库。
- 允许递归、允许每次现算、允许 O(N²)。禁止任何优化。
- 全仓库只有 `tests/reference.py` 允许用递归做 flood fill。
- 文件名不加 `test_` 前缀，避免被 pytest 收集为测试。
- `src/` 下任何文件不得 import 本模块。

## 4. 接口

```python
class RefBoard:
    def __init__(self, rows: int, cols: int,
                 mine_cells: frozenset[tuple[int, int]]) -> None:
        """雷位由外部给定；本类不布雷、不接触随机数。

        Raises:
            ValueError: rows/cols < 1；或 mine_cells 含越界坐标
                （消息含该坐标与棋盘尺寸）。
        """

    def in_bounds(self, r: int, c: int) -> bool:
        """0-based 坐标是否落在盘内。"""

    def adjacent(self, r: int, c: int) -> int:
        """现算 (r,c) 八邻域中的雷数，逐格遍历，O(8)。

        Raises:
            IndexError: (r,c) 越界。
        """

    def expand(self, r: int, c: int) -> set[tuple[int, int]]:
        """从 (r,c) 展开，返回本次新翻开的格子集合（含 (r,c) 自身）。

        Raises:
            IndexError: (r,c) 越界。
        """

    def revealed_numbers(self) -> dict[tuple[int, int], int]:
        """已翻开格 -> 其邻域数。未翻开的格子不得出现。"""
```

## 5. 展开语义（逐条实现，不得优化）

1. `(r, c)` 是雷 → 返回 `{(r, c)}`，不展开。
2. `(r, c)` 非雷 → `(r, c)` 必被翻开。
3. 仅当某格 `adjacent == 0` 时，才递归展开它的全部 8 个邻居。
4. 非零格只翻开自己，不向外传播。
5. 用 `visited` 集合记录已翻开格；重复遇到同一格不得重复递归。
6. 邻居必须裁剪到盘内：越界坐标不得进入 `visited`，也不得报错。

第 3、4 条最易写错，两类典型错误与对应抓它的用例：

| 错误 | 表现 | 抓它的用例 |
| --- | --- | --- |
| 无条件展开全部邻居 | 会翻开雷 | A |
| 只在 adj==0 时才翻开自己 | 漏掉边界上的非零格 | A、C |

## 6. 手算用例（权威值，测试断言以本文档为准）

### 用例 A：4×4，第 1 列整列为雷

雷位 `(0,1),(1,1),(2,1),(3,1)`，点击 `(0,3)`。

邻域数表（12 个非雷格）：

| 格 | adj | 格 | adj |
| --- | --- | --- | --- |
| (0,0) | 2 | (0,2) | 2 |
| (1,0) | 3 | (1,2) | 3 |
| (2,0) | 3 | (2,2) | 3 |
| (3,0) | 2 | (3,2) | 2 |
| — | — | (0,3) | 0 |
| — | — | (1,3) | 0 |
| — | — | (2,3) | 0 |
| — | — | (3,3) | 0 |

期望恰为 8 格：

```
{(0,2), (0,3), (1,2), (1,3), (2,2), (2,3), (3,2), (3,3)}
```

断言要点：左半 8 格 `(0,0)…(3,0)` 一格不得出现；雷格一格不得出现。

### 用例 B：同一盘面，点非零格

点击 `(1,0)`（adj=3）→ 期望 `{(1,0)}`，恰 1 格。
抓"非零格也向外传播"的错误。

### 用例 C：1×9，单雷在 (0,4)

邻域数 `[0,0,0,1,·,1,0,0,0]`（`·` 为雷）。点击 `(0,0)`。

期望恰为 4 格：

```
{(0,0), (0,1), (0,2), (0,3)}
```

抓"被非零格挡住"与单行棋盘上的邻居裁剪。

## 7. 必须写的测试（tests/test_reference.py）

正常（5 条）
- 用例 A / B / C 各一条，断言 `expand()` 返回集合与 §6 完全相等（用 `==` 比较 set）
- 5×5 全无雷、点中心 → 25 格全翻开，`revealed_numbers()` 全为 0
- `revealed_numbers()` 的键集合 == 最近一次 `expand()` 的返回集合

边界（4 条）
- 1×1 有雷 → `{(0,0)}`；1×1 无雷 → `{(0,0)}` 且 adj==0；1×2 全无雷点 (0,0) → 2 格
- 4×4 用例 A，点雷格 `(1,1)` → 返回 `{(1,1)}`，不展开
- 1×9 用例 C

异常（4 条）
- `expand(-1,0)`、`expand(0,9)` → `IndexError`
- `adjacent(4,0)` → `IndexError`
- `mine_cells` 含越界坐标 → `ValueError`，消息含该坐标
- `rows=0` 或 `cols=0` → `ValueError`

证据性实验（1 条，单独测试，供 docs/perf.md 引用）
```python
def test_experiment_recursion_limit_40x40():
    """固定递归上限后，本参考实现在 40×40 全 0 盘面触发 RecursionError，
    是正式实现选择迭代 BFS 的实测依据。"""
    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(1000)
    try:
        with pytest.raises(RecursionError):
            RefBoard(40, 40, frozenset()).expand(20, 20)
    finally:
        sys.setrecursionlimit(old)
```
必须显式设置并还原 recursionlimit，否则该测试依赖环境默认值，不可复现。

## 8. 允许新建 / 修改

- 允许新建：`tests/reference.py`、`tests/test_reference.py`
- 不得修改：`src/**`、`tests/test_board.py`、`tests/test_smoke.py`、
  `docs/**`、`.qoder/rules/**`、`pyproject.toml`、`examples/**`

## 9. 明确不做

- 不布雷（雷位由参数传入），不接触 `random`
- 不做 Game 的状态机、插旗、和弦、胜负判定
- 不做性能优化（缓存、预计算、改写成迭代）
- 不复用 `Board` 的任何代码

## 10. 交付方式（两轮）

第一轮：只输出文字，不改任何文件。给出

1. 逐方法实现思路（每个 ≤ 3 行）。
2. 对 §6 用例 A / B / C，逐格列出你算出的邻域数表（A 为 12 个非雷格），
   再写出从首点开始的展开顺序：每一步翻开了哪格、它的 adj、是否继续传播。
   最后给出结果集合并与 §6 对照；若不一致，说明你认为哪边错了。
3. 你认为本卡片存在歧义或错误的地方，没有就写"无"。

第二轮（等我确认后）：按确认的思路写代码，然后运行

```
.venv\Scripts\python.exe -m pytest -q --tb=short
```

粘贴完整真实输出与 `git diff --stat`。不得摘要，不得只说"已通过"。

## 11. 交付前自检

- `findstr /n "minesweeper" tests\reference.py` 无输出
- 未修改 `src/` 下任何文件
- pytest 全绿，测试总数比上一阶段多