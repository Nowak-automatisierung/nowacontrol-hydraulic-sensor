---
name: power-rf-battery-review
description: Review design choices for LiPo power, sleep and wake behavior, RF path, antenna constraints, and hardware validation needs.
---

Use this skill for battery, RF, and antenna related decisions.

Workflow:
1. Review the relevant hardware, firmware power logic, and product docs.
2. Identify:
   - battery path assumptions
   - peak current and brownout risks
   - antenna and enclosure sensitivities
   - measurement points required on real hardware
3. Separate facts from assumptions.
4. Recommend the minimum validation set before release.

Output format:
- Assumptions
- Risks
- Required measurements
- Recommended design and documentation updates
- Release impact