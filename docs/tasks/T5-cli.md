# T5 CLI 文本界面与示例回放

- 编号：T5
- 前置：S4 完成（插旗 / chord / mines_left 可用，tag v0.4-flags）
- 对应验收项：A8（同 seed 下 CLI 结果确定）、A10（示例可复现）
- 版本：v1

## 1. 任务

新建 `src/minesweeper/cli.py` 与 `src/minesweeper/__main__.py`，
提供可脚本化的文本界面；并建立 `examples/` 下的脚本与期望输出。

## 2. 必须遵循

- `.qoder/rules/00-architecture.md`
- `docs/decisions.md` 的 D1、D5、D15、D17、D18、D19
- 本任务**不得新增或修改 core 层的任何文件**

## 3. 接口

```python
# src/minesweeper/cli.py
def main(argv: list[str] | None = None) -> int:
    """解析参数、执行脚本、写出结果。

    返回进程退出码：0 正常，2 参数错误。
    """
```

命令行参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--rows` | 9 | 行数 |
| `--cols` | 9 | 列数 |
| `--mines` | 10 | 雷数 |
| `--seed` | None | 固定后盘面可复现；None 表示不可复现 |
| `--script` | None | 指令文件路径；缺省时进入交互模式 |
| `--out` | None | 输出文件路径；缺省写 stdout |

`src/minesweeper/__main__.py` 只做一件事：

```python
import sys
from .cli import main
raise SystemExit(main(sys.argv[1:]))
```

## 4. 指令格式

每行一条，字段以空白分隔；空行与 `#` 开头的行忽略。

| 指令 | 含义 | 对应 core 调用 |
| --- | --- | --- |
| `o R C` | 翻开 | `game.reveal(R, C)` |
| `f R C` | 插旗/撤旗 | `game.toggle_flag(R, C)` |
| `c R C` | 和弦 | `game.chord(R, C)` |
| `q` | 结束 | 停止读指令 |

R、C 为 0-based 整数。非法指令（字段数不对、非整数、越界坐标）：
向输出写一行 `ERROR <行号>: <原因>`，**继续执行后续指令**，不抛出异常。

## 5. 输出格式（必须逐字节稳定）

每次指令执行后输出一屏，格式固定：

```
9x9 mines=10 flags=1 state=PLAYING
.........
.111.....
.1F1.....
.111.....
.........
.........
.........
.........
.........
```

规则：

1. 首行：`<rows>x<cols> mines=<mines> flags=<已插旗数> state=<PLAYING|WON|LOST>`
2. 之后每行一个棋盘行，字符只允许：
   - `.` 未翻开
   - `F` 已插旗
   - `0`-`8` 已翻开的邻域数
   - `X` 被踩中的那颗雷（仅 LOST 且该格为 `exploded_cell`）
   - `*` 其余雷（仅 LOST）
3. 屏与屏之间用一个空行分隔
4. 结尾无多余空行；文件以单个 `\n` 结束
5. 只使用 ASCII 字符与 `\n` 换行

## 6. 硬性禁令

- `cli.py` **不得** import `board` / `rng`，不得出现 `is_mine`、`adjacent_at`、
  `_board`、`_revealed`、`_flagged`、`snapshot_mines` 中的任何一个名字
- `cli.py` 不得做任何雷数计算、展开、胜负判定；一切状态只从
  `game.state`、`game.view(r,c)`、`game.mines_left`、`game.revealed_cells` 读取
- 不得引入第三方依赖（不用 `argparse` 以外的东西；`argparse` 是标准库，允许）
- 任何地方不得读写 `examples/` 之外的路径

## 7. 允许修改

- 新建：`src/minesweeper/cli.py`、`src/minesweeper/__main__.py`
- 新建：`examples/seeds.md`、`examples/scripts/*.txt`、`examples/expected/*.txt`
- 新建：`tests/test_cli.py`
- 追加：`tests/test_architecture.py`（新增对 `cli.py` 的禁令扫描）
- 不得修改：`src/minesweeper/core/**`、`tests/reference.py`、
  `tests/test_against_reference.py`、`tests/test_game.py`、
  `tests/test_board.py`、`tests/test_reference.py`、`docs/**`、
  `README.md`、`.qoder/rules/**`、`pyproject.toml`

## 8. 必须建立的示例（三组）

`examples/seeds.md` 说明每组用途。脚本与期望输出成对存在：

| 脚本 | 参数 | 覆盖什么 |
| --- | --- | --- |
| `scripts/s42_beginner.txt` | `--rows 9 --cols 9 --mines 10 --seed 42` | 若干次 `o` + 一次 `f` + 一次错误指令 |
| `scripts/s7_mid.txt` | `--rows 16 --cols 16 --mines 40 --seed 7` | 中级规模、`o` 与 `c` 混合 |
| `scripts/s5_lose.txt` | `--rows 9 --cols 9 --mines 10 --seed 5` | 踩雷，覆盖 `X` 与 `*` 的渲染 |

**期望输出必须先由 CLI 生成，再逐字核对**：核对方法是看首行的
`flags` 与 `state` 是否正确、`X` 只出现一次、`*` 数量等于 mines 减去已踩的那颗。

## 9. 必须写的测试（tests/test_cli.py）

### 逐字节回放（核心）
- 对三组示例，调 `main([... , "--script", s, "--out", tmp])`，
  用 `Path(tmp).read_bytes()` 与 `examples/expected/<同名>.txt` 的
  `read_bytes()` 比较，断言完全相等
- 断言期望文件中**不含** `\r`

### 期望文件的独立校验（防止“用有 bug 的输出当金标准”）
- 对每组示例：用同一组参数新建 `Game`，按脚本执行同样的指令，
  然后逐格核对期望文件里的数字字符——每个已翻开的数字必须等于
  “以 `snapshot_mines()` 为真值、该格 8 邻域内雷的数量”
  （`snapshot_mines` 仅测试可用，这正是它的设计用途）

### 边界与异常
- 非法指令：字段数不对、`o a b`、`o 99 99` → 输出含 `ERROR`，且后续指令仍执行
- `--mines` 超过 D6 上限 → 退出码 2，输出含允许上界与传入值
- `--rows 0` → 退出码 2
- 空脚本 → 只输出初始屏（此时尚未布雷，全部为 `.`）
- 同 seed 两次运行 → 输出字节完全相同；不同 seed → 不同

### 架构
- `tests/test_architecture.py` 新增一条：`cli.py` 中不得出现
  `is_mine` / `adjacent_at` / `_board` / `_revealed` / `_flagged` / `snapshot_mines`
- 断言 `cli.py` 不 import `minesweeper.core.board` 或 `.rng`

## 10. 明确不做

- 不做交互式提示符、不做颜色、不做 ANSI 转义（保证逐字节可比）
- 不做计时、不做排行榜、不做存档
- 不修改 core 任何文件（若发现 core 接口不够用，先提出，不要自行扩展）

## 11. 交付方式（两轮）

**第一轮**：只输出文字，不改文件。给出

1. `main()` 的分段流程（参数解析 / 建 Game / 逐行读指令 / 渲染 / 写文件）；
2. 渲染函数如何保证“只读 `view()` 与 `state`”就能画出 `X` 与 `*`；
   说明为何 `WON` 时雷格显示为 `.`；
3. 你打算怎么构造第一组示例的脚本（列出具体指令序列与选择理由）；
4. 你认为卡片或决策记录有歧义的地方，没有就写“无”。

**第二轮**（确认后）：实现并运行

```bat
.venv\Scripts\python.exe -m pytest tests/test_cli.py -q --tb=short
```

粘贴完整输出与 `git diff --stat`。

## 12. 交付前自检

- `git diff --stat` 只含本任务允许的文件
- `tools/check_skeleton.py` → 仍 `未实现 0，空壳 0`
- 全量 pytest 全绿，总数比上阶段增加 10 条以上
- 期望文件均为纯 ASCII、LF 换行、结尾单个 `\n`