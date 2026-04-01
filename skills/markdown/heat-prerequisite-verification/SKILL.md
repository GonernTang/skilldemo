---
name: heat-prerequisite-verification
description: Use this skill before executing any heating action to guarantee the target object is securely placed within the heating appliance.
category: alfworld/heat
---

## Heat Prerequisite Verification

**Process:**
1. Identify the target object (e.g., cup, potato) and the heating device (microwave or stoveburner).
2. Navigate to the heating device.
3. Execute the 'put <object> in <device>' action to place the object inside.
4. Verify via observation that the object is now inside the device.
5. Execute the 'heat <object> with <device>' action.

**Anti-patterns:**
- Attempting to 'heat <object> with <device>' without first using the 'put' action to place the object inside.
- Assuming the object is inside the device simply because it was picked up previously without re-verifying its location.

**Failure Recovery:**
- If heating fails with 'Nothing happens', immediately check your inventory and surroundings to confirm the object's current location.
- Re-execute the 'put <object> in <device>' action if the object is not found inside the heating appliance.
