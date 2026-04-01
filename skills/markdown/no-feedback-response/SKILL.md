---
name: no-feedback-response
description: Agent continues executing actions that return 'Nothing happens' without adapting its strategy.
category: common_mistakes
---

## Do Not Ignore Action Failures

**Why it happens:**
The agent interprets 'Nothing happens' as a neutral state or successful execution, causing it to repeat the same futile actions (like opening non-existent or inaccessible containers) instead of pivoting.

**How to avoid:**
1. Treat 'Nothing happens' as a definitive signal that the action cannot be performed in the current state.
2. Immediately stop the current action sequence and re-evaluate the environment or try a different object/location.
