---
name: mg24-board-bringup
description: Bring up the XIAO MG24 device baseline, define firmware layout, and produce a board, flash, and test plan.
---

Use this skill when the task is to initialize or restructure the MG24 firmware baseline.

Workflow:
1. Inspect the current state of sensor-platform/firmware, tests, docs, and tools.
2. Produce a short bring-up plan with:
   - boot and build assumptions
   - board-specific boundaries
   - sensor HAL boundaries
   - flash and debug workflow
   - first measurable success criteria
3. Propose the minimal file structure needed for V1.
4. Identify unknowns that require bench validation.
5. End with a concrete next-step checklist.

Output format:
- Current state
- Bring-up plan
- Required files and folders
- Bench validation items
- Next 5 actions