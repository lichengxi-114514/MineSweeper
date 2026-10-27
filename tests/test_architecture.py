"""架构约束的机械检查。违反则测试失败，不依赖人工 review。"""
import ast
import pathlib

import pytest

SRC = pathlib.Path("src/minesweeper")


def _py_files(root: pathlib.Path):
    return sorted(root.rglob("*.py"))


def test_core_does_not_import_ui():
    """core 层禁止 import tkinter / argparse / 本项目 GUI 模块。"""
    forbidden = ("tkinter", "argparse", "minesweeper.gui", "minesweeper.cli")
    for p in _py_files(SRC / "core"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    assert not a.name.startswith(forbidden), f"{p}: import {a.name}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith(forbidden), f"{p}: from {mod} import ..."


def test_snapshot_mines_only_in_game_py():
    """snapshot_mines 会泄露完整雷位，只允许出现在 core/game.py 的定义处。"""
    allowed = SRC / "core" / "game.py"
    offenders = []
    for p in _py_files(SRC):
        if p == allowed:
            continue
        if "snapshot_mines" in p.read_text(encoding="utf-8"):
            offenders.append(str(p))
    assert not offenders, f"以下文件调用了 snapshot_mines: {offenders}"


def test_no_random_outside_rng():
    """除 core/rng.py 外，源码中不得出现 import random。"""
    allowed = SRC / "core" / "rng.py"
    for p in _py_files(SRC):
        if p == allowed:
            continue
        assert "import random" not in p.read_text(encoding="utf-8"), str(p)