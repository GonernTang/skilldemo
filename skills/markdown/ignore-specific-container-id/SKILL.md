---
name: ignore-specific-container-id
description: Agents frequently ignore the specific numeric ID required by the task (e.g., Cabinet-22) and default to searching nearby or low-numbered containers (e.g., Cabinet 1).
category: common_mistakes
---

## Mistake Title: Ignore Specific Container ID

**Why it happens:**
The agent parses the task type string loosely, treating the object category (e.g., 'Cabinet') as sufficient without extracting the mandatory unique identifier (e.g., '-22'). This leads to searching irrelevant locations like Cabinet 1 or Drawer 1 when the task explicitly demands Cabinet 22 or Drawer 409.

**How to avoid:**
1. Parse the task type string strictly to extract the target object ID (e.g., split 'Cabinet-22' to get '22').
2. Prioritize navigation commands targeting the exact ID found in the task description over general room scanning.
3. Verify the current object's ID matches the target ID before performing placement or pickup actions.
