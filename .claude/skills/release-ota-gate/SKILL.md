---
name: release-ota-gate
description: Evaluate whether a device change is ready for release and OTA rollout, including rollback and validation evidence.
disable-model-invocation: true
---

Use this skill when you explicitly want a release gate.

Task:
Assess whether the current change set is fit for release and OTA rollout.

Required review points:
1. What changed.
2. What was tested.
3. What was not tested.
4. Rollback path.
5. Pairing, rejoin, battery, telemetry, and update risks.
6. Whether the release should be blocked, staged, or approved.

Output format:
- Release summary
- Evidence available
- Missing evidence
- OTA and rollback assessment
- Final recommendation: BLOCK / STAGE / APPROVE