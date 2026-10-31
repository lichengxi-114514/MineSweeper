"""CLI 的测试：逐字节回放、独立校验、边界与异常、架构约束。"""
from __future__ import annotations

import ast
import pathlib

import pytest

from minesweeper.cli import main
from minesweeper.core import Game, GameState

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SCRIPTS = EXAMPLES / "scripts"
EXPECTED = EXAMPLES / "expected"
SRC = ROOT / "src" / "minesweeper"
CLI_PY = SRC / "cli.py"


# ========== 逐字节回放 ==========

@pytest.mark.parametrize(
    "name, args",
    [
        ("s42_beginner", ["--rows", "9", "--cols", "9", "--mines", "10", "--seed", "42"]),
        ("s7_mid", ["--rows", "16", "--cols", "16", "--mines", "40", "--seed", "7"]),
        ("s5_lose", ["--rows", "9", "--cols", "9", "--mines", "10", "--seed", "5"]),
    ],
)
def test_byte_exact_replay(name: str, args: list[str], tmp_path: pathlib.Path):
    """调 main 生成输出，与期望文件逐字节比对。"""
    script = str(SCRIPTS / f"{name}.txt")
    out_file = str(tmp_path / f"{name}.txt")
    rc = main(args + ["--script", script, "--out", out_file])
    assert rc == 0

    actual = pathlib.Path(out_file).read_bytes()
    expected = (EXPECTED / f"{name}.txt").read_bytes()
    assert actual == expected, (
        f"输出与期望不一致。\n"
        f"实际长度: {len(actual)}，期望长度: {len(expected)}\n"
        f"实际末尾 20 字节: {actual[-20:]!r}\n"
        f"期望末尾 20 字节: {expected[-20:]!r}"
    )


@pytest.mark.parametrize(
    "name",
    ["s42_beginner", "s7_mid", "s5_lose"],
)
def test_expected_file_no_cr(name: str):
    """期望文件不含 \\r（纯 LF 换行）。"""
    content = (EXPECTED / f"{name}.txt").read_bytes()
    assert b"\r" not in content


@pytest.mark.parametrize(
    "name",
    ["s42_beginner", "s7_mid", "s5_lose"],
)
def test_expected_file_ends_with_single_lf(name: str):
    """文件以单个 \\n 结束，无多余空行。"""
    content = (EXPECTED / f"{name}.txt").read_bytes()
    assert content.endswith(b"\n")
    assert not content.endswith(b"\n\n")


# ========== 期望文件的独立校验 ==========

def _verify_expected_independently(
    rows: int, cols: int, mines: int, seed: int,
    script_name: str,
):
    """用 snapshot_mines 逐格核对期望文件中的数字字符。"""
    g = Game(rows, cols, mines, seed=seed)
    script_path = SCRIPTS / script_name
    lines = script_path.read_text(encoding="utf-8").splitlines()

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        cmd = parts[0]
        if cmd == "q":
            break
        if cmd == "o":
            r, c = int(parts[1]), int(parts[2])
            if 0 <= r < g.rows and 0 <= c < g.cols:
                g.reveal(r, c)
        elif cmd == "f":
            r, c = int(parts[1]), int(parts[2])
            if 0 <= r < g.rows and 0 <= c < g.cols:
                g.toggle_flag(r, c)
        elif cmd == "c":
            r, c = int(parts[1]), int(parts[2])
            if 0 <= r < g.rows and 0 <= c < g.cols:
                g.chord(r, c)

    # 读取期望文件的最后一屏
    expected_text = (EXPECTED / script_name).read_text(encoding="ascii")
    # 按空行分屏
    screens = expected_text.strip().split("\n\n")
    # 最后一屏可能含 ERROR 行，需跳过
    last_screen = screens[-1]
    screen_lines = last_screen.split("\n")
    # 跳过 ERROR 行
    data_lines = [l for l in screen_lines if not l.startswith("ERROR")]
    if not data_lines:
        return

    header = data_lines[0]
    # 校验 header
    assert header.startswith(f"{rows}x{cols}")
    assert f"mines={mines}" in header

    # 校验每个格子
    mines_set = g.snapshot_mines()
    for r in range(rows):
        row_str = data_lines[1 + r]
        for c in range(cols):
            ch = row_str[c]
            v = g.view(r, c)
            # 计算期望字符
            if g.state is GameState.LOST and (r, c) == g.exploded_cell:
                exp = "X"
            elif v.mine:
                exp = "*"
            elif v.flagged:
                exp = "F"
            elif v.revealed:
                exp = str(v.adjacent)
                # 独立校验：adjacent 必须等于 8 邻域内雷数
                count = sum(
                    1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if (dr, dc) != (0, 0)
                    and 0 <= r + dr < rows and 0 <= c + dc < cols
                    and (r + dr, c + dc) in mines_set
                )
                assert int(exp) == count, (
                    f"({r},{ch}): adjacent={exp} 但实际雷数={count}"
                )
            else:
                exp = "."
            assert ch == exp, f"({r},{c}): got {ch!r}, expected {exp!r}"


def test_independent_verify_s42():
    _verify_expected_independently(9, 9, 10, 42, "s42_beginner.txt")


def test_independent_verify_s7():
    _verify_expected_independently(16, 16, 40, 7, "s7_mid.txt")


def test_independent_verify_s5():
    _verify_expected_independently(9, 9, 10, 5, "s5_lose.txt")


# ========== 边界与异常 ==========

def test_invalid_command_wrong_field_count(tmp_path: pathlib.Path):
    """字段数不对 → 输出含 ERROR，且后续指令仍执行。"""
    script = tmp_path / "bad.txt"
    script.write_text("o 1\no 0 0\nq\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    rc = main(["--rows", "9", "--cols", "9", "--mines", "10", "--seed", "1",
               "--script", str(script), "--out", str(out)])
    assert rc == 0
    content = out.read_text(encoding="ascii")
    assert "ERROR" in content
    # 后续指令 o 0 0 应被执行：检查是否有第二屏（初始屏 + ERROR 后的屏 + o 0 0 后的屏）
    screens = content.strip().split("\n\n")
    assert len(screens) >= 2


def test_invalid_command_non_integer(tmp_path: pathlib.Path):
    """o a b → 输出含 ERROR。"""
    script = tmp_path / "bad.txt"
    script.write_text("o a b\nq\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    rc = main(["--rows", "9", "--cols", "9", "--mines", "10", "--seed", "1",
               "--script", str(script), "--out", str(out)])
    assert rc == 0
    content = out.read_text(encoding="ascii")
    assert "ERROR" in content


def test_invalid_command_out_of_bounds(tmp_path: pathlib.Path):
    """o 99 99 → 输出含 ERROR。"""
    script = tmp_path / "bad.txt"
    script.write_text("o 99 99\nq\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    rc = main(["--rows", "9", "--cols", "9", "--mines", "10", "--seed", "1",
               "--script", str(script), "--out", str(out)])
    assert rc == 0
    content = out.read_text(encoding="ascii")
    assert "ERROR" in content


def test_mines_exceeds_upper_bound(tmp_path: pathlib.Path):
    """--mines 超过 D6 上限 → 退出码 2。"""
    out = tmp_path / "out.txt"
    rc = main(["--rows", "9", "--cols", "9", "--mines", "73", "--seed", "1",
               "--out", str(out)])
    assert rc == 2


def test_rows_zero(tmp_path: pathlib.Path):
    """--rows 0 → 退出码 2。"""
    out = tmp_path / "out.txt"
    rc = main(["--rows", "0", "--cols", "9", "--mines", "0",
               "--out", str(out)])
    assert rc == 2


def test_empty_script(tmp_path: pathlib.Path):
    """空脚本 → 只输出初始屏（尚未布雷，全部为 .）。"""
    script = tmp_path / "empty.txt"
    script.write_text("", encoding="utf-8")
    out = tmp_path / "out.txt"
    rc = main(["--rows", "9", "--cols", "9", "--mines", "10", "--seed", "1",
               "--script", str(script), "--out", str(out)])
    assert rc == 0
    content = out.read_text(encoding="ascii")
    # 只有一屏，无空行分隔
    assert "\n\n" not in content
    # 首行应为 state=PLAYING
    assert "state=PLAYING" in content
    # 全部为 .
    lines = content.strip().split("\n")
    for line in lines[1:]:
        assert all(ch == "." for ch in line)


def test_same_seed_same_output(tmp_path: pathlib.Path):
    """同 seed 两次运行 → 输出字节完全相同。"""
    script = tmp_path / "s.txt"
    script.write_text("o 4 4\nq\n", encoding="utf-8")
    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"
    args = ["--rows", "9", "--cols", "9", "--mines", "10", "--seed", "42",
            "--script", str(script)]
    main(args + ["--out", str(out1)])
    main(args + ["--out", str(out2)])
    assert out1.read_bytes() == out2.read_bytes()


def test_different_seed_different_output(tmp_path: pathlib.Path):
    """不同 seed → 输出不同。"""
    script = tmp_path / "s.txt"
    script.write_text("o 4 4\nq\n", encoding="utf-8")
    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"
    base = ["--rows", "9", "--cols", "9", "--mines", "10", "--script", str(script)]
    main(base + ["--seed", "1", "--out", str(out1)])
    main(base + ["--seed", "2", "--out", str(out2)])
    assert out1.read_bytes() != out2.read_bytes()


# ========== 架构 ==========

def test_cli_does_not_import_forbidden_modules():
    """cli.py 不 import board / rng。"""
    tree = ast.parse(CLI_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        for name in names:
            assert "minesweeper.core.board" not in name, f"cli.py import {name}"
            assert "minesweeper.core.rng" not in name, f"cli.py import {name}"
            # 也检查相对导入
            if name.startswith("."):
                assert "board" not in name, f"cli.py import {name}"
                assert "rng" not in name, f"cli.py import {name}"


def test_cli_does_not_reference_forbidden_names():
    """cli.py 中不得出现 is_mine / adjacent_at / _board / _revealed / _flagged / snapshot_mines。"""
    source = CLI_PY.read_text(encoding="utf-8")
    forbidden = ["is_mine", "adjacent_at", "_board", "_revealed", "_flagged", "snapshot_mines"]
    for name in forbidden:
        assert name not in source, f"cli.py 包含禁用名字: {name}"
