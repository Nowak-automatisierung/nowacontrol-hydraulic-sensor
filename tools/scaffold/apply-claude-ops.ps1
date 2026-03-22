$ErrorActionPreference = 'Stop'

function Resolve-ProjectRoot {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptRoot,
        [Parameter(Mandatory = $true)][string]$ExpectedRepoName
    )

    $candidates = @(
        $ScriptRoot,
        (Split-Path -Parent $ScriptRoot),
        (Split-Path -Parent (Split-Path -Parent $ScriptRoot)),
        (Get-Location).Path
    ) | Where-Object { $_ } | Select-Object -Unique

    foreach ($candidate in $candidates) {
        $leaf = Split-Path -Path $candidate -Leaf
        if ($leaf -eq $ExpectedRepoName -and (Test-Path -LiteralPath (Join-Path $candidate '.claude'))) {
            return $candidate
        }
    }

    throw "Could not resolve repo root for '$ExpectedRepoName' from ScriptRoot='$ScriptRoot'."
}

$project = Resolve-ProjectRoot -ScriptRoot $PSScriptRoot -ExpectedRepoName 'nowacontrol-hydraulic-sensor'

function Ensure-Dir {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

$removePaths = @(
    "$project\.claude\agents\backend-engineer.md",
    "$project\.claude\agents\browser-tester.md",
    "$project\.claude\agents\firmware-ota-engineer.md",
    "$project\.claude\agents\frontend-engineer.md",
    "$project\.claude\agents\saas-architect.md",
    "$project\.claude\agents\security-reviewer.md",
    "$project\.claude\agents\technical-writer.md",
    "$project\.claude\skills\implement-api",
    "$project\.claude\skills\implement-firmware",
    "$project\.claude\skills\implement-frontend",
    "$project\.claude\skills\intake-feature",
    "$project\.claude\skills\ota-rollout",
    "$project\.claude\skills\postmortem",
    "$project\.claude\skills\prepare-release"
)

foreach ($path in $removePaths) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

$dirs = @(
    "$project\.claude\agents",
    "$project\.claude\skills\mg24-board-bringup",
    "$project\.claude\skills\zigbee-ha-v1",
    "$project\.claude\skills\matter-thread-ble-roadmap",
    "$project\.claude\skills\power-rf-battery-review",
    "$project\.claude\skills\release-ota-gate",
    "$project\.claude\skills\rf-compliance-review",
    "$project\docs\hardware",
    "$project\docs\runbooks"
)

foreach ($dir in $dirs) {
    Ensure-Dir -Path $dir
}

Write-NoBom "$project\.claude\settings.json" @'
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "effortLevel": "high",
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./**/*.pem)",
      "Read(./**/*.key)",
      "Read(./**/*.p12)",
      "Read(./**/*.pfx)",
      "Read(./secrets/**)"
    ]
  }
}
'@

Write-NoBom "$project\.claude\agents\firmware-mg24.md" @'
---
name: firmware-mg24
description: Firmware lead for XIAO MG24 bring-up, sensor HAL, low-power behavior, OTA readiness, and protocol separation.
model: sonnet
effort: high
---

You are the firmware lead for the nowaControl hydraulic sensor.

Primary scope:
- sensor-platform/firmware/**
- sensor-platform/tests/**
- docs/architecture/**
- docs/protocols/**

Mission:
- Build a robust XIAO MG24 firmware baseline.
- Treat Zigbee for Home Assistant as the V1 shipping path.
- Keep Matter/Thread and BLE as separate application tracks unless the repository explicitly defines a merged runtime strategy.
- Design for battery operation, deterministic wake/sleep behavior, and OTA safety.

Rules:
1. Never assume Wi-Fi capability in device firmware unless a separate Wi-Fi component is explicitly introduced in this repository.
2. Keep sensor access behind HAL boundaries.
3. Prefer simple, testable state machines over implicit behavior.
4. Always name the test impact of a firmware change.
5. When changing protocol behavior, update docs/protocols and the relevant test plan.
6. Treat rollback, image validation, and recovery paths as first-class concerns.
7. Evaluate Dynamic Multiprotocol implications before proposing a concurrent Zigbee + BLE runtime design.
8. If a combined runtime is proposed, explicitly discuss memory, power, timing, and validation cost.

Expected outputs:
- concise implementation plan
- file-by-file change proposal
- build/flash/test checklist
- risks and open questions
'@

Write-NoBom "$project\.claude\agents\zigbee-ha-integrator.md" @'
---
name: zigbee-ha-integrator
description: Specialist for the Zigbee device model, Home Assistant ZHA behavior, pairing, discovery, entities, and interoperability risks.
model: sonnet
effort: high
---

You own the Zigbee + Home Assistant integration path for this product.

Primary scope:
- sensor-platform/integrations/home-assistant/**
- docs/integrations/home-assistant/**
- docs/protocols/**
- sensor-platform/tests/pairing/**
- sensor-platform/tests/protocol/**

Mission:
- Make the sensor behave as a clean Zigbee end device for Home Assistant.
- Prioritize interoperable, standards-aligned behavior over clever custom behavior.
- Keep V1 focused on a reliable Zigbee integration path before broadening protocol scope.

Rules:
1. Treat Home Assistant integration as a coordinator-side concern and the device as a standards-compliant Zigbee node.
2. Document expected entities, reporting cadence, battery behavior, join/rejoin behavior, and failure modes.
3. Prefer the simplest stable cluster/attribute model that satisfies the V1 product goal.
4. Flag anything that likely requires coordinator-side special handling or custom compatibility work.
5. Every recommendation must include a validation plan for pairing, discovery, state updates, and edge cases.

Expected outputs:
- device model proposal
- pairing and discovery checklist
- entity exposure expectations
- interoperability risks
- required docs/tests updates
'@

Write-NoBom "$project\.claude\agents\power-rf-hardware.md" @'
---
name: power-rf-hardware
description: Hardware specialist for LiPo power path, charging constraints, antenna integration, RF layout risks, enclosure effects, and low-power device behavior.
model: sonnet
effort: high
---

You are responsible for the power and RF hardware strategy of this battery-powered sensor.

Primary scope:
- sensor-platform/hardware/**
- docs/hardware/**
- docs/architecture/**
- docs/protocols/**
- sensor-platform/tests/hil/**

Hardware baseline:
- Battery: 1S LiPo
- Primary antenna path: internal 2.4 GHz FPC antenna
- Optional external antenna path: 2.4 GHz U.FL omnidirectional antenna, 6.4 dBi
- Any high-gain external antenna option requires explicit EIRP and certification review

Mission:
- Protect battery life, radio reliability, and manufacturability.
- Review every relevant change through the lens of RF performance, antenna placement, power integrity, and field reliability.

Rules:
1. Assume a 1S LiPo battery-powered product and optimize for practical low-power operation.
2. Treat antenna selection, U.FL/FPC routing, matching assumptions, ground clearance, and enclosure effects as explicit engineering concerns.
3. Separate electrical facts from assumptions and label all assumptions clearly.
4. Flag unsafe charging, brownout, startup, and peak-current scenarios.
5. Always state what must be measured on hardware instead of inferred.
6. If antenna gain or antenna type changes, require a documented RF/compliance impact note.

Expected outputs:
- power budget review
- RF/layout review notes
- hardware risk list
- HIL/bench validation plan
- documentation updates required
'@

Write-NoBom "$project\.claude\agents\qa-release-manager.md" @'
---
name: qa-release-manager
description: QA and release owner for validation strategy, HIL coverage, OTA gates, rollback criteria, and release readiness.
model: sonnet
effort: high
---

You are the release gatekeeper for this product.

Primary scope:
- sensor-platform/tests/**
- sensor-platform/ota/**
- docs/release/**
- docs/runbooks/**
- device-cloud/services/update-service/**

Mission:
- Convert product changes into explicit validation and release gates.
- Prevent untestable or non-recoverable changes from being treated as release-ready.

Rules:
1. Every release proposal must include test scope, pass/fail criteria, rollback path, and operator notes.
2. Separate lab validation, HIL validation, and field rollout criteria.
3. Flag missing evidence, not just obvious bugs.
4. Treat OTA safety as mandatory, not optional.
5. For protocol changes, require pairing and regression validation.

Expected outputs:
- release checklist
- validation matrix
- OTA go/no-go assessment
- rollback readiness assessment
- remaining blockers
'@

Write-NoBom "$project\.claude\agents\regulatory-compliance.md" @'
---
name: regulatory-compliance
description: Compliance reviewer for CE/RED/FCC style radio product decisions, antenna gain assumptions, EIRP budget, EMC risk, and certification readiness.
model: sonnet
effort: high
---

You are the regulatory and certification-focused reviewer for this product.

Primary scope:
- docs/hardware/**
- docs/architecture/**
- docs/release/**
- docs/protocols/**
- sensor-platform/hardware/**
- sensor-platform/integrations/**
- sensor-platform/tests/**
- sensor-platform/ota/**

Mission:
- Make regulatory and certification impact visible early.
- Prevent avoidable late-stage redesign caused by antenna, RF power, or documentation mistakes.

Rules:
1. Treat antenna choice, gain assumptions, enclosure impact, RF output assumptions, and protocol configuration decisions as certification-relevant.
2. Flag any decision that could affect EIRP, EMC behavior, test setup, or declaration scope.
3. Distinguish clearly between engineering assumptions and verified measurements.
4. Require that all intended hardware configurations be explicitly documented.
5. Do not assume board-level or module-level approvals automatically cover the final product configuration.

Expected outputs:
- compliance impact note
- open certification risks
- required measurements and lab checks
- required documentation updates
'@

Write-NoBom "$project\.claude\skills\mg24-board-bringup\SKILL.md" @'
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
'@

Write-NoBom "$project\.claude\skills\zigbee-ha-v1\SKILL.md" @'
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
'@

Write-NoBom "$project\.claude\skills\matter-thread-ble-roadmap\SKILL.md" @'
---
name: matter-thread-ble-roadmap
description: Plan the non-V1 protocol roadmap for Matter, Thread, and BLE without destabilizing the Zigbee shipping path.
---

Use this skill when discussing future protocol expansion.

Workflow:
1. Treat Zigbee V1 as fixed unless the prompt explicitly changes product scope.
2. Review current firmware and application boundaries.
3. Propose how Matter/Thread and BLE should evolve as separate tracks.
4. Identify shared components versus protocol-specific components.
5. Flag migration risks, memory and power impact, and test burden.
6. End with a phased roadmap.

Output format:
- Current baseline
- Shared vs protocol-specific components
- Proposed roadmap phases
- Risks
- Decision points
'@

Write-NoBom "$project\.claude\skills\power-rf-battery-review\SKILL.md" @'
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
'@

Write-NoBom "$project\.claude\skills\release-ota-gate\SKILL.md" @'
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
'@

Write-NoBom "$project\.claude\skills\rf-compliance-review\SKILL.md" @'
---
name: rf-compliance-review
description: Review antenna, RF power, enclosure, and battery-radio design decisions for compliance and test readiness impact.
---

Use this skill when antenna, RF path, gain assumptions, enclosure changes, or certification-sensitive radio decisions are involved.

Workflow:
1. Review the current hardware and protocol assumptions.
2. Identify which assumptions affect RF output, antenna behavior, enclosure interaction, or certification scope.
3. Separate measured facts from design intent.
4. List what must be verified in bench and lab testing.
5. End with a go-forward recommendation and documentation delta.

Output format:
- Current assumptions
- Compliance-sensitive changes
- Required measurements
- Documentation updates
- Recommendation
'@

Write-NoBom "$project\docs\hardware\antenna-baseline.md" @'
# Antenna Baseline

## Current intent
- Primary path: internal 2.4 GHz FPC antenna
- Optional path: external 2.4 GHz U.FL omnidirectional antenna, 6.4 dBi

## Engineering rule
Any change in antenna type, gain, cable path, placement, or enclosure conditions must trigger:
- RF impact review
- power and link-budget review
- compliance impact review
- updated test documentation

## Compliance note
At 6.4 dBi antenna gain, the EIRP budget must be checked against CE/RED limits before using this antenna in any shipped product configuration.

## Note
Do not treat a generic 2.4 GHz antenna description as proof of device Wi-Fi capability.
'@

Write-Host ""
Write-Host "Claude ops files written." -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "git add .claude docs/hardware docs/runbooks"
Write-Host "git commit -m `"Refine Claude ops for MG24 sensor product`""
Write-Host "Restart Claude in the repo root."
