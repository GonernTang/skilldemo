---
name: execute-cool-workflow
description: Use when the task requires cooling an object in a fridge before placing it in a final location.
category: alfworld/cool
---

## Execute Cool Workflow

**Process:**
1. Locate the target object specified in the task goal.
2. Navigate to a functional fridge in the environment.
3. Place the target object inside the fridge to initiate cooling.
4. Wait for the cooling process to complete.
5. Take the cooled object from the fridge.
6. Navigate to the designated final receptacle (e.g., shelf).
7. Place the cooled object into the final receptacle.

**Anti-patterns:**
- Attempting to cool an object without physically placing it inside the fridge first.
- Forgetting to retrieve the object from the fridge before attempting to place it in the final destination.

**Failure Recovery:**
- If the fridge is locked or full, locate an alternative fridge or clear space before proceeding.
- If the object remains hot after retrieval, return it to the fridge and allow more time to pass.
