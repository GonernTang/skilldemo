---
name: heat-object-inside-appliance
description: Use when you need to heat an object like an apple using a microwave or stoveburner.
category: alfworld/heat
---

## Heat Object Inside Appliance

**Process:**
1. Locate the target object (e.g., apple) and a heating appliance (microwave or stoveburner).
2. Pick up the target object.
3. Navigate to the heating appliance.
4. Place the object INSIDE the appliance (e.g., "put apple in microwave").
5. Execute the heat action on the appliance (e.g., "heat microwave").
6. Take the heated object OUT of the appliance (e.g., "take apple from microwave") before moving to the final location.

**Anti-patterns:**
- Attempting to heat an object without placing it inside the appliance first.
- Trying to move the object to the final destination without retrieving it from the appliance first.

**Failure Recovery:**
- If the heat action says "Nothing happens," verify the object is actually inside the appliance.
- If the object cannot be taken, wait for the heating cycle to complete or check if the appliance is open.
