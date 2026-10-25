"""MineSweeper —— 可复现、首点安全、带逻辑求解器的扫雷。

分层约定：
    minesweeper.core  —— 纯逻辑，禁止 import 任何 UI 模块
    minesweeper.cli   —— 文本界面
    minesweeper.gui   —— Tkinter 界面
"""

__version__ = "0.1.0"