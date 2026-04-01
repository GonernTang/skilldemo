---
name: secure-heat-execution
description: Use this skill when heating an object to ensure correct placement inside the appliance and handle potential state inconsistencies.
category: alfworld/heat
---

## Secure Heating Execution

**Process:**
1. Navigate to the target appliance (microwave or stoveburner).
2. Open the appliance if it is currently closed.
3. Move the target object inside the appliance using `move <object> to <appliance>`.
4. Verify the object is inside by observing the appliance contents.
5. Execute the heat command (`heat <appliance>` or `heat <object> with <appliance>`).
6. If heating completes, open the appliance and take the object out (`take <object> from <appliance>`).

**Anti-patterns:**
- Attempting to heat an object without first moving it inside the appliance.
- Attempting to retrieve the object while the appliance door is closed.

**Failure Recovery:**
- If "Nothing happens" occurs during heating, reopen the appliance to verify the object is present.
- If unable to take the object out, ensure the appliance is fully opened before retrying the take action.
- If one appliance consistently fails, switch to an alternative heating source (e.g., stoveburner instead of microwave).
