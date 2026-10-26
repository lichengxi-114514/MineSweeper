## 案例 0：AI 指出我的验收标准自相矛盾（S2，Board 层）
- 场景：给 Qoder 的 T2 任务卡片中的边界用例
- 我的原始要求：「1×1 棋盘，mines=1 应抛 ValueError」
- Qoder 提出：Board(1,1) 无 forbid 时候选数 = 1、mines = 1，
  按 `<` 判定应成功；该用例与「9×9 角首点 mines=77 应成功」互斥
- 我的判断：它是对的。我把 Game 层（D6=B 的全局上界）的约束
  误写进了 Board 层测试，属于层级混淆
- 处理：Board 层改为 place_mines(rng, 1, forbid={(0,0)}) 抛 ValueError；
  「1×1 放 1 雷被拒」移到 S3 由 Game 层验证
- 验证：Board(1,1)+forbid 抛 ValueError；Board(9,9)+角 forbid 下 mines=77 成功
- 状态：已采纳并修正任务卡片（commit: 见 git log）
## 案例 1：实现与换行符规则进入同一提交
- 观察：f3b8aee 的信息为 "chore: 统一换行符为 LF"，
  实际包含 .gitattributes 与 board.py / rng.py / test_board.py 三类改动
- 后果：git log 中不存在独立的 feat(core) 条目；
  标签 v0.2-board 指向一条信息与内容不符的提交
- 已确认的根因：提交前未逐文件核对 git diff --cached --stat
- 未确认、不作断言：具体是哪条 add 命令把实现文件一并暂存的
- 处理：保留已推送历史不改写，标签指向 f3b8aee，内容完整可核验
- 验证：全新克隆中 git ls-files 含三个实现文件，pytest 31 passed
- 后续约定：git add 一律显式列文件名；提交前必看 git diff --cached --stat