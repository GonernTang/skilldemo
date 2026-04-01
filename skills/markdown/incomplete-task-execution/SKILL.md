---
name: incomplete-task-execution
description: Terminating the search or action sequence before fulfilling all required sub-goals.
category: common_mistakes
---

## Do Not Stop Before Completing Objectives

**Why it happens:**
The agent halts its process prematurely, either due to reaching a step limit or giving up after initial failures, leaving tasks like 'pick two objects' or 'place item' unfinished.

**How to avoid:**
1. Maintain a checklist of all required sub-goals (e.g., count of objects needed).
2. Continue searching or interacting until every sub-goal is verified as complete.
3. Ensure placement actions are executed after picking, not just picking alone.
