---
name: repeated-action-loop
description: Repeating the same action multiple times after receiving negative feedback like 'Nothing happens'.
category: common_mistakes
---

## Do Not Repeat Invalid Actions

**Why it happens:**
The agent fails to interpret negative feedback ('Nothing happens') as a signal to change strategy, leading to redundant attempts on the same object or location.

**How to avoid:**
1. Monitor action outcomes; if 'Nothing happens' occurs, stop attempting that specific action.
2. Re-evaluate the object's state or location before trying again.
3. Switch to a different search strategy or container if the current approach yields no results.
