"""CLI 文本界面：脚本化执行与逐字节稳定输出。

设计依据见 docs/decisions.md D17、D18、D19。
硬性约束（§6）：
    - 不 import board / rng
    - 不使用 core 内部属性与雷位查询接口
    - 一切状态只从 game.state / game.view(r,c) / game.mines_left / game.revealed_cells 读取
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import Game, GameState


def _render_screen(g: Game, out) -> None:
    """渲染一屏到 out（file-like）。

    字符集（D17）：
        .  未翻开
        F  已插旗
        0-8  已翻开的邻域数
        X  被踩中的雷（仅 LOST 且为 exploded_cell）
        *  其余雷（仅 LOST）

    LOST 时单格优先级：X > * > F > 0-8 > .
    """
    flags = sum(
        1 for r in range(g.rows) for c in range(g.cols)
        if g.view(r, c).flagged
    )
    out.write(
        f"{g.rows}x{g.cols} mines={g.mines} flags={flags} state={g.state.name}\n"
    )
    for r in range(g.rows):
        chars: list[str] = []
        for c in range(g.cols):
            v = g.view(r, c)
            # 优先级：X > * > F > 0-8 > .
            if g.state is GameState.LOST and (r, c) == g.exploded_cell:
                chars.append("X")
            elif v.mine:          # 仅 LOST 时为 True
                chars.append("*")
            elif v.flagged:
                chars.append("F")
            elif v.revealed:
                chars.append(str(v.adjacent))
            else:
                chars.append(".")
        out.write("".join(chars) + "\n")


def _parse_coord(s: str) -> int:
    """解析坐标字符串为 int，失败抛 ValueError。"""
    return int(s)


def _in_bounds_public(g: Game, r: int, c: int) -> bool:
    """用公开属性自查越界，不访问 _in_bounds。"""
    return 0 <= r < g.rows and 0 <= c < g.cols


def main(argv: list[str] | None = None) -> int:
    """解析参数、执行脚本、写出结果。

    返回进程退出码：0 正常，2 参数错误。
    """
    parser = argparse.ArgumentParser(description="Minesweeper CLI")
    parser.add_argument("--rows", type=int, default=9)
    parser.add_argument("--cols", type=int, default=9)
    parser.add_argument("--mines", type=int, default=10)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--script", type=str, default=None)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args(argv)

    # 建 Game；让 core 的 ValueError 自然抛出，CLI 捕获后 return 2
    try:
        g = Game(args.rows, args.cols, args.mines, seed=args.seed)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # 打开输出通道
    if args.out:
        out_file = open(args.out, "w", encoding="ascii", newline="\n")
    else:
        out_file = sys.stdout

    try:
        first = True

        def emit_screen() -> None:
            nonlocal first
            if not first:
                out_file.write("\n")
            _render_screen(g, out_file)
            first = False

        # 初始屏
        emit_screen()

        # 读指令
        if args.script:
            lines = Path(args.script).read_text(encoding="utf-8").splitlines()
        else:
            lines = sys.stdin.read().splitlines()

        for line_no, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            cmd = parts[0]

            if cmd == "q":
                break

            if cmd in ("o", "f", "c"):
                if len(parts) != 3:
                    out_file.write(f"ERROR {line_no}: wrong field count\n")
                    emit_screen()
                    continue
                try:
                    r = _parse_coord(parts[1])
                    c = _parse_coord(parts[2])
                except ValueError:
                    out_file.write(f"ERROR {line_no}: non-integer coordinate\n")
                    emit_screen()
                    continue
                if not _in_bounds_public(g, r, c):
                    out_file.write(f"ERROR {line_no}: coordinate out of bounds\n")
                    emit_screen()
                    continue

                if cmd == "o":
                    g.reveal(r, c)
                elif cmd == "f":
                    g.toggle_flag(r, c)
                elif cmd == "c":
                    g.chord(r, c)
            else:
                out_file.write(f"ERROR {line_no}: unknown command\n")
                emit_screen()
                continue

            emit_screen()
    finally:
        if args.out:
            out_file.close()

    return 0
