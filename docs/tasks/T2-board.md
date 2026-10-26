## 任务
实现 src/minesweeper/core/rng.py 与 board.py（按文件内已有的接口骨架逐方法实现）。
不实现 Game。先只输出实现思路 + 边界用例清单，等我确认后再写代码。

## 必须遵循
- .qoder/rules/00-architecture.md、10-testing.md
- docs/decisions.md D1/D2/D5（D3/D4 在 Game 层，本任务只需 protected_cells/max_mines_at）

## 实现约束
1. 存储：一维 bytearray，长度 (rows+2)*(cols+2)，哨兵边框恒为 0。
   真实格偏移 = (r+1)*W + (c+1)，W = cols+2。换算只在 _off() 里写一次。
2. 偏移表：self._offsets 是**一个 8 元组**常量（由 W 决定），不是每格一张表。
   预计算邻域数时直接迭代它，读到的边框格天然是 0，无需任何 if 分支。
3. 公开接口全部 0-based；边框绝不外泄（neighbors 必须裁剪）。
4. 预计算：布雷后遍历真实格，sum(mine[off + o] for o in offsets)。
   遍历范围只含真实格，边框的邻域值保持 0。
5. 抽样：rng.sample(候选列表, mines)。禁止 while 重抽。
6. place_mines 只能成功调用一次（内部 flag，重复调用抛 RuntimeError）。
7. 除 rng.py 外禁止 import random；禁止递归；禁止第三方库。
8. 一个函数 ≤ 40 行；公开方法写 docstring。

## 只允许改动
- 新建/修改：src/minesweeper/core/rng.py、src/minesweeper/core/board.py
- 新建：tests/test_board.py
不得修改：tests/test_smoke.py、tests/reference.py（尚不存在）、examples/、
docs/、src/minesweeper/gui/**、pyproject.toml、.qoder/rules/**

## 测试要求（每个用例写清"测什么性质"）
正常：
  - 9×9/10 雷：mine_count == 10；所有格 adjacent_at == count_adjacent_raw
  - forbid 生效：protected_cells(4,4,9,9) 的 9 格全部 is_mine == False（100 次）
  - fingerprint 相同 seed 相同；不同 seed 不同
  - to_hex 往返：from_hex(to_hex()) 后 fingerprint 一致
边界（逐条必测）：
  - 1×1：mines=0 成功；mines=1 抛 ValueError
  - 1×3：端点首点 mines=1 成功；中点首点 mines=1 抛 ValueError
  - 2×2：任何首点 max_mines_at == 0
  - 3×3：角 max_mines_at == 5，中心 == 0
  - 9×9：角 77 / 边上非角 75 / 内部 72 —— 三种各取一个坐标断言
  - neighbors：角上 3 个、边上 5 个、内部 8 个；全部落在 [0, rows) × [0, cols)
  - 越界查询：is_mine(-1,0) / is_mine(0,cols) / neighbors(-1,-1) 的行为符合契约
异常：
  - place_mines 重复调用 → RuntimeError
  - mines=-1 → ValueError；mines=候选+1 → ValueError，且消息含所需与可用两个数字

## 明确不做
自动展开、Game 状态机、胜负判定、GUI、性能优化、R3

- **不得修改任何方法签名与 docstring 的契约部分**。docstring 里的
  Raises / 复杂度 / 禁止事项是验收依据；若你认为契约有误，先提出，
  不要自行修改。允许在 docstring 末尾追加实现说明。
- 骨架里已实现的 `__init__` 与 `_off()` 不得改写（除非我先同意）。
- 完成后自查： `findstr /s /n "NotImplementedError" src\minesweeper\core\board.py`
  必须无输出。