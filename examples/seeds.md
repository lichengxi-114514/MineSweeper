# 示例种子说明

本目录存放 CLI 的脚本化回放示例。每组由脚本（`scripts/`）与期望输出（`expected/`）成对组成，
用于逐字节比对测试（`tests/test_cli.py`）。

## 三组示例

| 脚本 | 参数 | 覆盖什么 |
| --- | --- | --- |
| `scripts/s42_beginner.txt` | `--rows 9 --cols 9 --mines 10 --seed 42` | 若干次 `o` + 一次 `f` + 一次错误指令 |
| `scripts/s7_mid.txt` | `--rows 16 --cols 16 --mines 40 --seed 7` | 中级规模、`o` 与 `c` 混合 |
| `scripts/s5_lose.txt` | `--rows 9 --cols 9 --mines 10 --seed 5` | 踩雷，覆盖 `X` 与 `*` 的渲染 |

## 坐标来源

- **s42_beginner** 与 **s7_mid**：坐标从渲染出的屏上选取（等价于玩家可见信息）。
  作者运行 CLI 后观察盘面，选择未翻开的格进行 `o` / `f` / `c` 操作。
- **s5_lose**：`(0, 3)` 的坐标由作者离线用 `snapshot_mines()` 确定为雷位，
  CLI 本身不读取雷位。该坐标仅用于触发 LOST 状态以验证 `X` 与 `*` 的渲染。

## 期望输出的生成与校验

期望输出由 CLI 自身生成（`--out` 参数），然后经独立校验：
用同一组参数新建 `Game`，执行同样的指令序列，逐格核对期望文件中的数字字符，
确认每个已翻开的数字等于"以 `snapshot_mines()` 为真值、该格 8 邻域内雷的数量"。
