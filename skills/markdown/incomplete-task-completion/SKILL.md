---
name: incomplete-task-completion
description: Agent locates the target object but fails to execute the remaining required interaction steps.
category: common_mistakes
---

## Do Not Stop After Locating Target

**Why it happens:**
The agent successfully navigates to find the target object (Apple on diningtable) but fails to execute the subsequent required actions (pick, heat, place), causing the task to end prematurely.

**How to avoid:**
1. Track all sub-goals defined in the task type (e.g., pick, heat, place) and ensure each is completed.
2. Once the object is located, immediately attempt the first interaction action instead of continuing to navigate.
3. Verify the final state matches the task objective before terminating the episode.
