---
name: heat-microwave-procedure
description: Use when heating an object like a mug using a microwave or stoveburner.
category: alfworld/heat
---

## Heat Object Procedure

**Process:**
1. Navigate to the target object and pick it up.
2. Move to the heating appliance (microwave or stoveburner).
3. Open the appliance if it is a microwave.
4. Move the object inside the appliance.
5. Execute the heat action.
6. Take the object out after heating.

**Anti-patterns:**
- Attempting to heat an object while holding it outside the appliance.
- Ignoring the appliance door status (e.g., trying to heat through a closed microwave).

**Failure Recovery:**
- If heating returns "Nothing happens", verify the object is visible inside the appliance by opening it.
- If the object is missing, return to the previous location to retrieve it.
