# 评论区需求

> 2026-06-05 更新：评审 UI 重构完成

## 身份

- **作者**：可在所有评审的 Thread 中回复；自评置顶
- **评审人**：可在自己的评审 Thread 中回复；自己的评审 hover 可编辑星星
- **旁观者（已登录）**：可查看所有评审和 Thread，只读
- **未登录**：可查看所有评审和 Thread，只读

池内/池外：
- 池内评审显示匿名名，出池后匿名不变
- 池外评审显示实名
- 自评始终显示实名

## 基本构件：评论（Review Card）

每条评论包含：
- **评论者名称**（实名/匿名/Author）
- **五维分数**：O/R/C/P/I 数字显示；自己的评审 hover 展开为可编辑星星
- **发布时间**
- **Thread 下拉抽屉**：Chevron 展开/折叠，iMessage 风格聊天气泡

### 两种模式

| 模式 | 分数显示 | Thread 操作 |
|------|---------|------------|
| 我是评审人 | 数字显示（`O:4 R:3 C:5`），hover 某维展开为可编辑星星 | 可回复 |
| 我不是评审人 | 数字显示（同），无 hover 交互 | 作者+评审人可回复，旁观者只读 |

## 评审提交流程

1. 未评审 → 显示空的五维星星 + 评论文本框 + "Submit Review" 按钮
2. 首次评论 → POST review + POST 首条 thread message（若有）
3. 已评审 → 显示分数数字 + Thread 下拉；可修改星星

## Thread 规则

- **参与者**：文章作者 + 该评审的评审人
- **旁观者**：看到 "Only the author and reviewer can participate in this thread"
- **空 Thread**：自己的评审无 Thread 时显示输入框 "Start a conversation..."
- **风格**：iMessage 聊天气泡（作者左对齐深色，回复者右对齐 accent 色）

## 排序

- 当前用户的评审始终置顶（accent 色左边框 + "(you)" 标签）
- 其次是作者自评（"Author (self-review)"）
- 最后按发布时间降序

## 星星

- 尖锐五角星（HeroIcon path `M12 2l3.09 6.26L22 9.27...`）
- 金色（`#f0c040`），通过 CSS custom properties 控制
- 大小 `sm`（w-3 h-3）用于评论中的内联显示
