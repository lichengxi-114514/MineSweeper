"""架构约束的机械检查。

违反即测试失败，不依赖人工 review。
判据一律用 AST 而非字符串匹配：字符串无法区分
"import random 仅用于类型注解" 与 "用 random 产生随机性"。
"""
from __future__ import annotations

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "minesweeper"
GAME = SRC / "core" / "game.py"
RNG = SRC / "core" / "rng.py"

FORBIDDEN_IN_CORE = ("tkinter", "argparse", "minesweeper.gui", "minesweeper.cli")


def py_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(root.rglob("*.py"))


def test_core_does_not_import_ui():
    """core 层禁止 import UI / CLI 或本项目任何界面模块。"""
    for p in py_files(SRC / "core"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert not name.startswith(FORBIDDEN_IN_CORE), (
                    f"{p}:{node.lineno} import {name}"
                )


def test_snapshot_mines_only_in_game_py():
    """snapshot_mines 会泄露完整雷位，只允许出现在 core/game.py 的定义处。"""
    offenders = [
        str(p)
        for p in py_files(SRC)
        if p != GAME and "snapshot_mines" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, "以下文件引用了 snapshot_mines: " + "; ".join(offenders)


def test_no_randomness_outside_rng():
    """除 core/rng.py 外，源码不得 *产生* 随机性。

    允许：仅用于类型注解的 import random（不产生随机性）。
    禁止：调用 random 模块的任何函数；from random import ...。
    随机性只能由 rng.make_rng(seed) 返回的实例产生，且该实例由构造函数注入。
    """
    offenders: list[str] = []
    for p in py_files(SRC):
        if p == RNG:
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        aliases: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "random":
                        aliases.add(a.asname or "random")
            elif isinstance(node, ast.ImportFrom) and node.module == "random":
                offenders.append(f"{p}:{node.lineno}: from random import ...")

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if (
                isinstance(f, ast.Attribute)
                and isinstance(f.value, ast.Name)
                and f.value.id in aliases
            ):
                offenders.append(f"{p}:{node.lineno}: {f.value.id}.{f.attr}(...)")

    assert not offenders, "在 rng.py 之外产生随机性: " + "; ".join(offenders)


def test_rng_module_exists():
    """rng.py 是唯一随机入口，必须存在且导出 make_rng。"""
    assert RNG.is_file(), f"缺少 {RNG}"
    tree = ast.parse(RNG.read_text(encoding="utf-8"))
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "make_rng" in names, "rng.py 未定义 make_rng"


# ========== CLI 架构约束（T5）==========

CLI_PY = SRC / "cli.py"
FORBIDDEN_IN_CLI = (
    "is_mine", "adjacent_at", "_board", "_revealed", "_flagged", "snapshot_mines",
)


def test_cli_does_not_reference_forbidden_names():
    """cli.py 中不得出现 is_mine / adjacent_at / _board / _revealed / _flagged / snapshot_mines。"""
    assert CLI_PY.is_file(), f"缺少 {CLI_PY}"
    source = CLI_PY.read_text(encoding="utf-8")
    for name in FORBIDDEN_IN_CLI:
        assert name not in source, f"cli.py 包含禁用名字: {name}"


def test_cli_does_not_import_board_or_rng():
    """cli.py 不 import board / rng。"""
    assert CLI_PY.is_file(), f"缺少 {CLI_PY}"
    tree = ast.parse(CLI_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        for name in names:
            assert "board" not in name, f"cli.py import {name}"
            assert "rng" not in name, f"cli.py import {name}"