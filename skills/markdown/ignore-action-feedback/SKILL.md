---
name: ignore-action-feedback
description: Common mistake: Agent ignores 'Nothing happens' feedback and persists with invalid actions.
category: common_mistakes
---

## Ignore Negative Feedback

**Why it happens:**
The agent treats negative environmental feedback ('Nothing happens') as noise rather than a critical signal to halt and reassess, leading to repetitive invalid attempts.

**How to avoid:**
1. Detect 'Nothing happens' responses immediately after an action.
2. Halt the current action sequence and do not repeat the same attempt.
3. Re-evaluate the object's location or the room state before choosing a new strategy.
