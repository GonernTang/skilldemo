---
name: heat-object-procedure
description: Use when heating an object to ensure correct placement and handle action failures.
category: alfworld/heat
---

## Heat Object Procedure

**Process:**
1. Move the target object inside the microwave or stoveburner.
2. Ensure the appliance door is open to verify placement.
3. Execute the heat action with the appliance.
4. If heating succeeds, open the appliance and take the object out.

**Anti-patterns:**
- Attempting to heat an object that is not confirmed inside the appliance.
- Trying to retrieve an object from a closed appliance without opening it first.

**Failure Recovery:**
- If "Nothing happens" occurs during heating, reopen the appliance to verify the object is actually inside.
- If retrieval fails, ensure the appliance is fully open before attempting to take the object again.
