## 案例 0：AI 指出我的验收标准自相矛盾
- 场景：S2 任务卡片里的边界用例
- 我的原始要求：1×1 棋盘 mines=1 应抛 ValueError
- Qoder 提出：Board 层无 forbid 时候选数=1、mines=1、按 `<` 判定应成功；
  该用例与"高密度 9×9 mines=77 应成功"互斥
- 我的判断：它是对的，我把 Game 层的 D6 约束误写进了 Board 层测试
- 处理：Board 层改为 forbid={(0,0)} 后 mines=1 抛错；Game 层上限另测
- 验证：Board(1,1)+forbid 抛 ValueError；Board(9,9)+角 forbid 下 mines=77 成功