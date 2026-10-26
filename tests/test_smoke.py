"""最小冒烟测试：确认包可导入、pytest 配置生效。"""

import minesweeper
import minesweeper.core


def test_version():
    assert minesweeper.__version__


def test_core_package_importable():
    assert minesweeper.core is not None
    
def test_package_installed_editable():
    """若未 pip install -e . ，python -m minesweeper 会失败；
    这里用 importlib 的 find_spec 做一次快速断言，避免到了 GUI 阶段才发现。"""
    import importlib.util
    spec = importlib.util.find_spec("minesweeper")
    assert spec is not None
    assert spec.origin is not None
    assert spec.origin.endswith("__init__.py")