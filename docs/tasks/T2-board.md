# T2：Board 盘面层实现

## 任务
按 src/minesweeper/core/board.py 中已有的接口骨架逐方法实现
（rng.py 一并实现）。不实现 Game。先只输出实现思路 + 边界用例清单，
等我确认后再写代码。

## 上下文
- 骨架文件：src/minesweeper/core/board.py（14 处 NotImplementedError）
- 需求：docs/requirements.md 的 A1、A2、A4（A4 已按 D6=B 修订）
- 决策：docs/decisions.md D1、D2、D5、D6
- 规则：.qoder/rules/00-architecture.md、10-testing.md

## 实现约束
1. 存储：一维 bytearray，长度 (rows+2)*(cols+2)，哨兵边框恒为 0。
   真实格偏移 = (r+1)*W + (c+1)，W = cols+2。换算只在 _off() 里写一次。
2. 偏移表：self._offsets 是**一个 8 元组**（由 W 决定），不是每格一张表。
3. 公开接口全部 0-based；边框绝不外泄。
4. 预计算：布雷后只遍历真实格，直接迭代 self._offsets，
   边框格天然为 0，**不得出现任何 if 越界判断**。
5. 抽样：rng.sample(候选列表, mines)，禁止 while 重抽。
6. place_mines 只能成功调用一次（_placed 标志，重复调用抛 RuntimeError）。
7. 候选不足判定用 `<`（候选数 == 雷数 时全部为雷，合法）。
   报错消息必须含：所需雷数、可用格数、forbid 规模三个数字。
8. 除 rng.py 外禁止 import random；禁止递归；禁止第三方库。
9. 一个函数 <= 40 行；公开方法保留骨架 docstring，可在末尾追加实现说明。
10. to_hex 编码：每格 1 字节 = 高 4 位雷位(0/1) | 低 4 位邻域数(0-8)，
   小写 hex、无分隔、无换行；长度恰为 2*rows*cols。
   from_hex 必须校验，任一不满足抛 ValueError（消息含原因与首个出错坐标）：
   (a) 去空白后长度 == 2*rows*cols；(b) 全为 hex 字符；
   (c) 高 4 位 <= 1；(d) 低 4 位 <= 8；
   (e) 由雷位重算的邻域数必须与低 4 位逐一相等。
   校验通过后置 _placed=True、_mine_count=雷位数。
11. 唯一批准新增的成员是私有方法 _precompute_adjacent()，由 place_mines
    与 from_hex 共用。不得新增其他方法，不得改任何签名。

### 契约保护（硬约束，违反即视为任务失败）
12. **不得修改任何方法签名，也不得改动 docstring 中描述契约的部分**
    （Args / Raises / 返回值语义 / 复杂度 / 禁止事项）。
    若你认为契约有误，先提出来等我确认，不要自行修改。
13. **骨架里已实现的 `__init__` 与 `_off()` 不得改写**（除非我先同意）。

## 只允许改动
- 修改：src/minesweeper/core/board.py、src/minesweeper/core/rng.py
- 新建：tests/test_board.py
- 不得触碰：tests/test_smoke.py、tests/reference.py（尚不存在）、
  examples/、docs/、src/minesweeper/gui/**、pyproject.toml、.qoder/rules/**

## 测试要求
每条用例注明"测什么性质"。不得修改现有测试，不得加 skip/xfail。

### 正常
- 9×9 / 10 雷：mine_count == 10；所有真实格 adjacent_at == count_adjacent_raw
- forbid 生效：protected_cells(4,4,9,9) 的 9 格 is_mine 全为 False（重复 100 次）
- 同 seed 两次 place_mines → fingerprint 相同；不同 seed → 不同
- to_hex 往返：from_hex(to_hex()) 后 fingerprint 一致
- fingerprint 长度 == 2*(rows+2)*(cols+2)；to_hex 长度 == 2*rows*cols
- 角上单雷：只在 (0,0) 放一颗雷时 adjacent_at(0,1)/adjacent_at(1,0)/adjacent_at(1,1) 均 == 1
- protected_cells 必须含自身：(r,c) in protected_cells(r,c,rows,cols)；
  protected_cells(4,4,9,9) 长度为 9
- from_hex 还原后再 place_mines → RuntimeError；mine_count 等于雷位数

### 边界
- 1×1：place_mines(rng, 0) 成功；place_mines(rng, 1, forbid={(0,0)}) 抛 ValueError。
  （"1×1 放 1 雷被拒"属于 Game 层 D6=B 的约束，不在 Board 层验证）
- 2×2：任意格 max_mines_at == 0
- 3×3：角 max_mines_at == 5，中心 == 0
- 9×9：角 77 / 边上非角 75 / 内部 72（三种各取一个坐标断言）
- protected_max：min(rows,3)*min(cols,3)；与"遍历所有格取最大值"的暴力版
  在 1×1…9×9 共 20 组尺寸上一致
- neighbors：角 3 个、边上 5 个、内部 8 个；全部落在 [0,rows) × [0,cols)
- 高密度：9×9 角上首点、mines=77 成功；mines=78 抛 ValueError
- neighbors 与 _offsets 交叉验证：对 9×9 全部 81 格断言
  set(neighbors(r,c)) == {(r+dr,c+dc) for 八方向 if in_bounds}，数量相等
- mines == 候选数 的边界成功用例：3×3 角首点、mines=5 → 成功，
  5 个非保护格全为雷、4 个保护格全非雷

### 异常
- place_mines 重复调用 → RuntimeError
- mines=-1 → ValueError
- mines=候选格数+1 → ValueError，消息含三个数字
- is_mine(-1,0)、is_mine(0,cols)、adjacent_at(rows,0) → IndexError（不返回 False）
- neighbors(-1,-1) → IndexError（不返回空迭代器）
- Board(0,5)、Board(5,0) → ValueError
- from_hex 五类坏样本各抛 ValueError：长度错 / 非 hex 字符 /
  高 4 位 == 2 / 低 4 位 == 9 / adj 与雷位矛盾
## 自查（交付前必须执行并粘贴输出）
```bat
findstr /n "NotImplementedError" src\minesweeper\core\board.py | find /c "NotImplementedError"
.venv\Scripts\python.exe -m pytest -q