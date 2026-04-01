---
name: validate-object-and-placement-for-heating
description: Use when initiating a heating task to ensure the selected object matches the task requirements and is correctly situated within the heating device.
category: alfworld/heat
---

## Validate Object and Placement for Heating

**Process:**
1. Read the task description to identify the required object type (e.g., Mug).
2. Search the environment for the specific object type, avoiding similar items (e.g., Cups).
3. Navigate to the appropriate heating appliance (Microwave, Stove, etc.).
4. Open the appliance if it is closed.
5. Move the object into the appliance or onto the burner.
6. Inspect the appliance interior to confirm the object is present.
7. Attempt the heat action only after confirmation.

**Anti-patterns:**
- Do not proceed with heating using a generic object (like a Cup) if the task specifies a specific type (like a Mug).
- Do not assume the heating action succeeded without verifying the object remains inside the appliance afterward.
