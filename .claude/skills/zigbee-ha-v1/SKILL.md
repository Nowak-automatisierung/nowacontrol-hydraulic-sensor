---
name: zigbee-ha-v1
description: Design or review the V1 Zigbee path for Home Assistant, including device model, pairing, reporting, and validation.
---

Use this skill for any V1 work on the Zigbee + Home Assistant path.

Workflow:
1. Review docs/integrations/home-assistant and sensor-platform/integrations/home-assistant.
2. Define or review:
   - device role
   - cluster and attribute behavior
   - battery and reporting behavior
   - pairing and rejoin expectations
   - expected Home Assistant entities
3. Keep the design minimal and interoperability-first.
4. Identify where documentation, tests, or coordinator-side notes are missing.
5. End with a validation matrix.

Output format:
- Proposed V1 device behavior
- Expected HA outcome
- Risks and compatibility concerns
- Required tests
- Required repo changes