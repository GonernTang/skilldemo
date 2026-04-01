---
name: incomplete-task-verification
description: Agent stops or repeats actions without confirming task completion
category: common_mistakes
---

## Mistake Title

**Why it happens:**
Agents fail to verify task completion after executing sub-goals. In trajectory 1, the agent immediately executed 'done' without any action. In trajectory 2, the agent completed the cooling and placing task but then entered a loop of 'stop' actions (steps 9-11, 13-20) instead of confirming success.

**How to avoid:**
1. After completing all required sub-tasks, explicitly check if the final state matches task requirements
2. Avoid repeating 'stop' or 'done' actions without verification feedback
3. Confirm task completion by checking observation messages for success indicators before ending
