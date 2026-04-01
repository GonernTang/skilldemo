---
name: validate-action-prerequisites
description: Common mistake: Executing actions without checking system constraints such as inventory capacity, container state, or object compatibility.
category: common_mistakes
---

## Do Not Execute Without Checking State

**Why it happens:**
Agents frequently attempt actions that violate environmental rules, such as holding two objects simultaneously or interacting with appliances in incorrect states. Trajectory 3 failed because the agent tried to pick a second candle while already holding one, exceeding inventory limits. Trajectory 2 failed repeatedly because it attempted to heat a cup in a microwave and use it with a coffee machine without ensuring the correct interaction sequence or object compatibility.

**How to avoid:**
1. Check current inventory count before attempting to pick up a new object; store or place existing items first if capacity is limited.
2. Verify appliance states (open/closed) and object compatibility before issuing interaction commands (e.g., heating, using).
3. Observe feedback messages (e.g., 'Nothing happens') immediately and adjust the action plan rather than repeating the same invalid command.
