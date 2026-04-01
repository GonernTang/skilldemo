---
name: ignore-negative-feedback
description: Agent ignores "Nothing happens" feedback and persists with invalid actions or halts progress.
category: common_mistakes
---

## Ignore Negative Feedback

**Why it happens:**
The agent receives "Nothing happens" indicating an action failed or is invalid, but interprets it as a temporary glitch or ignores it, continuing the same action or freezing instead of adapting.

**How to avoid:**
1. Treat "Nothing happens" as a hard stop for the current action sequence.
2. Re-evaluate the object's location and state before retrying.
3. If an action consistently fails, switch to an alternative method or verify prerequisites (e.g., is the container closed?).
