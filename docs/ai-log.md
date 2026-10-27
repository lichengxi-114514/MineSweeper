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

## 案例 2：参考实现的状态语义未被定义
- 场景：T3a 第一轮，Qoder 指出 §4 的 expand 契约（返回本次新增）与
  §7 测试要求（revealed_numbers() 键集合 == 返回值）只在首次调用时自洽
- 我的判断：它是对的，且根因是我的卡片漏写了“跨调用是否累积”这一语义，
  不是测试写错了
- 未采纳的部分：它建议“只要测试只调用一次 expand 就成立”——这会回避而非
  定义语义；S3c 需要在同一盘面连续点击比对，语义必须明确
- 处理：将 RefBoard 定为有状态（_revealed 累积），expand 返回 delta；
  补充重复点击返回空集合的规则与用例
- 验证：新增 3 条测试（累积并集、重复点击、已翻开雷格），全绿

## 案例 3：架构测试的判据过宽导致假阳性
- 现象：test_no_randomness_outside_rng 失败，指向 board.py 的 import random
- 核查：该 import 仅用于 place_mines 的参数注解 random.Random；board.py 顶部
  有 from __future__ import annotations，注解运行时不求值；随机性全部来自
  注入的 rng 实例（rng.sample 为实例方法）
- 判断：被测代码正确，是断言判据过宽（字符串匹配 vs AST 调用检查）
- 处理：测试改为 AST 级检查 random 模块的函数调用；规则文本同步修正为
  "禁止产生随机性"而非"禁止 import"
- 界线说明：改动的是"检查什么性质"，而非放宽既有断言；被测代码未改动
- 反证：向 game.py 注入一次 random.sample 调用，测试按预期变红，撤回后恢复
- 意外收获：该失败证明了机械检查确实在运行，不是摆设

## 案例 4：交叉验证的两处设计补强
- 背景：T3c 第一轮，Qoder 的流程与三条断言均正确，第 2 问
  （踩雷时两侧集合为何仍相等）也答对了，指出 revealed_cells 只记录
  "点击/展开直接翻开的格"，不包含 LOST 后显示层额外揭示的雷
- 我的补强一：它丢弃了 ref.expand 的返回值。补上 set(ref_delta) == set(delta)，
  可抓到"两侧 delta 同时少报同一格"这类累计集合无法暴露的缺陷
- 我的补强二：原卡片要求"1000 局中至少出现一局 WON"，实际依赖运气。
  改为确定性用例——mines=0 首点全开必 WON；主动从
  snapshot_mines()-revealed_cells 取雷点开必 LOST
- 它提出的类型细节（delta == [cell] 为有序比较）判断正确：踩雷只有一格，
  保留有序比较还额外验证了"返回值恰为一格"
- 教训：AI 提出的"这是否违反一律 set 比较"能促成一次真正的契约讨论，
  比单纯接受或驳回更有价值