"""列出 src/ 下所有方法及其实现状态，用于检查骨架完成度。

用法：
    python tools/check_skeleton.py            # 只列未实现与空壳
    python tools/check_skeleton.py --all      # 列出全部方法
"""
from __future__ import annotations

import ast
import pathlib
import sys

SRC = pathlib.Path("src/minesweeper")


def _is_docstring(s: ast.stmt) -> bool:
    return (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
            and isinstance(s.value.value, str))


def _body_without_docstring(node: ast.FunctionDef) -> list[ast.stmt]:
    return [s for s in node.body if not _is_docstring(s)]


def _raises_not_implemented(node: ast.FunctionDef) -> bool:
    """识别两种写法：raise NotImplementedError / raise NotImplementedError()"""
    stmts = _body_without_docstring(node)
    if len(stmts) != 1 or not isinstance(stmts[0], ast.Raise):
        return False
    exc = stmts[0].exc
    if isinstance(exc, ast.Call):
        exc = exc.func
    return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"


def _is_shell(node: ast.FunctionDef) -> bool:
    """只有 pass / ... / 无语句 —— 静默返回 None，比未实现更危险。"""
    stmts = _body_without_docstring(node)
    if not stmts:
        return True
    if len(stmts) == 1:
        s = stmts[0]
        if isinstance(s, ast.Pass):
            return True
        if (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                and s.value.value is Ellipsis):
            return True
    return False


def _report(label: str, node: ast.FunctionDef,
            pending: list[str], shells: list[str], show_all: bool) -> None:
    if _raises_not_implemented(node):
        pending.append(label)
    elif _is_shell(node):
        shells.append(label)
    elif show_all:
        print(f"  ok  {label}")


def main() -> int:
    show_all = "--all" in sys.argv
    total_cls = total_mod = 0
    pending: list[str] = []
    shells: list[str] = []

    for p in sorted(SRC.rglob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))

        # 1) 类体内的方法：xxx.py:NN  Class.method
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for node in cls.body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                total_cls += 1
                _report(f"{p}:{node.lineno}  {cls.name}.{node.name}",
                        node, pending, shells, show_all)

        # 2) 模块级函数：xxx.py:NN  <module>.name（rng.make_rng 属于此类）
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                total_mod += 1
                _report(f"{p}:{node.lineno}  <module>.{node.name}",
                        node, pending, shells, show_all)

    print("\n== 未实现（raise NotImplementedError）==")
    print("\n".join(pending) if pending else "  （无）")
    print("\n== 空壳（pass / ... / 仅 docstring）==")
    print("\n".join(shells) if shells else "  （无）")
    print(f"\n类方法 {total_cls}，模块级函数 {total_mod}，"
          f"合计 {total_cls + total_mod}；未实现 {len(pending)}，空壳 {len(shells)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())