---
name: repeat-unsuccessful-actions
description: When an action returns 'Nothing happens', the agent repeats the exact same command multiple times instead of diagnosing the failure or checking environmental state.
category: common_mistakes
---

## Mistake Title: Repeat Unsuccessful Actions

**Why it happens:**
The agent interprets 'Nothing happens' as a temporary latency issue rather than a hard constraint violation (e.g., trying to put an item in a closed drawer, or picking up an item that isn't there). This results in wasted steps and failure to adapt the strategy.

**How to avoid:**
1. Treat 'Nothing happens' as a critical failure signal requiring immediate state verification.
2. Before retrying, check if prerequisites are met (e.g., is the drawer open? is the object visible in the observation?).
3. If the action fails twice, switch strategies (e.g., try a different container or look for the object elsewhere) rather than looping.
