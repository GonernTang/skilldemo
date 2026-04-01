---
name: verify-task-completion-state
description: Use before signaling task completion to ensure all objectives are visibly satisfied in the environment.
category: general
---

## VERIFY TASK COMPLETION STATE

**Process:**
1. After performing the final manipulation step, review the current observation.
2. Confirm the target object is in the correct location and state (e.g., placed, cleaned, heated).
3. Only execute 'task complete' if the observation matches the task requirements.
4. If unsure, perform a quick scan of the destination area to confirm presence.

**Anti-patterns:**
- Calling 'task complete' immediately after the last movement without checking the result.
- Assuming the task is done based on intent rather than environmental observation.

**Failure Recovery:**
- If 'task complete' returns 'Nothing happens', re-evaluate the scene for missing steps.
- Return to the destination location and verify the object is actually placed there.
