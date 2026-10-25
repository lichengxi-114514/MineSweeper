"""最小冒烟测试：确认包可导入、pytest 配置生效。"""

import minesweeper
import minesweeper.core


def test_version():
    assert minesweeper.__version__


def test_core_package_importable():
    assert minesweeper.core is not None