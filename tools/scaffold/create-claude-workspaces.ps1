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

    throw "Could not resolve repo root for '$ExpectedRepoName' from script root '$ScriptRoot'."
}

function Ensure-Dir {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Utf8NoBom {
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

function Test-BranchExists {
    param(
        [Parameter(Mandatory = $true)][string]$Repo,
        [Parameter(Mandatory = $true)][string]$Branch
    )

    & git -C $Repo show-ref --verify --quiet "refs/heads/$Branch"
    return ($LASTEXITCODE -eq 0)
}

function Assert-GitClean {
    param(
        [Parameter(Mandatory = $true)][string]$Project
    )

    $status = & git -C $Project status --porcelain=v1
    if ($LASTEXITCODE -ne 0) {
        throw "git status failed in: $Project"
    }

    if ($status) {
        throw "Repo nicht clean. Erst committen oder stashen, dann Worktrees erzeugen."
    }
}

function Assert-ClaudeOpsCommitted {
    param(
        [Parameter(Mandatory = $true)][string]$Project
    )

    $requiredTrackedFiles = @(
        '.claude/agents/firmware-mg24.md',
        '.claude/agents/zigbee-ha-integrator.md',
        '.claude/agents/power-rf-hardware.md',
        '.claude/agents/qa-release-manager.md',
        '.claude/agents/regulatory-compliance.md',
        '.claude/skills/mg24-board-bringup/SKILL.md',
        '.claude/skills/zigbee-ha-v1/SKILL.md',
        '.claude/skills/matter-thread-ble-roadmap/SKILL.md',
        '.claude/skills/power-rf-battery-review/SKILL.md',
        '.claude/skills/release-ota-gate/SKILL.md',
        '.claude/skills/rf-compliance-review/SKILL.md',
        '.claude/settings.json',
        'docs/hardware/antenna-baseline.md'
    )

    foreach ($file in $requiredTrackedFiles) {
        & git -C $Project ls-files --error-unmatch -- $file 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Claude-Ops-Layer nicht committed oder Datei fehlt in Git: $file. Erst 'git add' + 'git commit' ausführen."
        }
    }
}

function Assert-OutsideRepo {
    param(
        [Parameter(Mandatory = $true)][string]$Project,
        [Parameter(Mandatory = $true)][string]$CandidatePath
    )

    $projectFull = [System.IO.Path]::GetFullPath($Project).TrimEnd('\')
    $candidateFull = [System.IO.Path]::GetFullPath($CandidatePath).TrimEnd('\')

    if (
        $candidateFull.Equals($projectFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $candidateFull.StartsWith($projectFull + '\', [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "Worktree root must be outside the repository root: $candidateFull"
    }
}

function Ensure-Worktree {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Definition,
        [Parameter(Mandatory = $true)][string]$WorktreeRoot
    )

    $path = Join-Path $WorktreeRoot $Definition.Name
    $branchExists = Test-BranchExists -Repo $project -Branch $Definition.Branch

    if (Test-Path -LiteralPath $path) {
        if (-not (Test-Path -LiteralPath (Join-Path $path '.git'))) {
            throw "Path exists but is not a git worktree: $path"
        }

        Write-Host "Worktree already exists: $path" -ForegroundColor Yellow
    }
    else {
        if ($branchExists) {
            & git -C $project worktree add $path $Definition.Branch
        }
        else {
            & git -C $project worktree add -b $Definition.Branch $path HEAD
        }

        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create worktree: $($Definition.Name)"
        }
    }

    $scopeLines = ($Definition.Scope | ForEach-Object { "- $_" }) -join "`r`n"
    $topicLines = ($Definition.FocusTopics | ForEach-Object { "- $_" }) -join "`r`n"

    Write-Utf8NoBom -Path (Join-Path $path 'WORKSPACE-FOCUS.md') -Content @"
# Workspace: $($Definition.Name)

## Branch
$($Definition.Branch)

## Primary agent
$($Definition.Agent)

## Primary scope
$scopeLines

## Focus topics
$topicLines

## Goal
$($Definition.Goal)

## Working rule
- Keep this workspace narrow.
- Do not mix unrelated changes into this branch.
- Use this workspace for one major stream only.
"@

    Write-Utf8NoBom -Path (Join-Path $path 'open-claude.ps1') -Content @'
Set-Location -LiteralPath $PSScriptRoot
claude
'@
}

$project = Resolve-ProjectRoot -ScriptRoot $PSScriptRoot -ExpectedRepoName 'nowacontrol-hydraulic-sensor'

$gitRoot = (& git -C $project rev-parse --show-toplevel 2>$null).Trim()
if (-not $gitRoot) {
    throw "Git repository not found: $project"
}

if ((Resolve-Path $gitRoot).Path -ne (Resolve-Path $project).Path) {
    throw "Script must resolve to repo root: $project"
}

Assert-GitClean -Project $project
Assert-ClaudeOpsCommitted -Project $project

$worktreeBase = Join-Path (Split-Path -Parent $project) 'worktrees'
$worktreeRoot = Join-Path $worktreeBase (Split-Path -Path $project -Leaf)

Assert-OutsideRepo -Project $project -CandidatePath $worktreeRoot
Ensure-Dir -Path $worktreeRoot

$definitions = @(
    @{
        Name        = 'firmware-mg24'
        Branch      = 'ws/firmware-mg24'
        Agent       = 'firmware-mg24'
        Scope       = @(
            'sensor-platform/firmware/**',
            'sensor-platform/tests/**',
            'docs/architecture/**',
            'docs/protocols/**'
        )
        FocusTopics = @(
            'EFR32MG24 bring-up',
            'GSDK firmware baseline',
            'Dynamic Multiprotocol implications',
            'OTA readiness and rollback safety'
        )
        Goal        = 'Establish the MG24 firmware baseline, HAL boundaries, low-power behavior, and the first bring-up/test plan for V1.'
    }
    @{
        Name        = 'zigbee-ha'
        Branch      = 'ws/zigbee-ha'
        Agent       = 'zigbee-ha-integrator'
        Scope       = @(
            'sensor-platform/integrations/home-assistant/**',
            'docs/integrations/home-assistant/**',
            'docs/protocols/**',
            'sensor-platform/tests/pairing/**',
            'sensor-platform/tests/protocol/**'
        )
        FocusTopics = @(
            'ZHA behavior',
            'zigbee2mqtt compatibility risks',
            'Cluster and attribute mapping',
            'Pairing, reporting, and rejoin behavior'
        )
        Goal        = 'Define the V1 Zigbee device model for Home Assistant and document the minimal interoperable behavior.'
    }
    @{
        Name        = 'power-rf-hardware'
        Branch      = 'ws/power-rf-hardware'
        Agent       = 'power-rf-hardware'
        Scope       = @(
            'sensor-platform/hardware/**',
            'docs/hardware/**',
            'docs/architecture/**',
            'docs/protocols/**',
            'sensor-platform/tests/hil/**'
        )
        FocusTopics = @(
            'LiPo 1S power path',
            'Battery peak current and brownout risk',
            'FPC vs U.FL antenna path',
            'CE/RED relevant RF constraints'
        )
        Goal        = 'Review the power and RF baseline for battery life, antenna strategy, enclosure sensitivity, and required bench validation.'
    }
    @{
        Name        = 'qa-release'
        Branch      = 'ws/qa-release'
        Agent       = 'qa-release-manager'
        Scope       = @(
            'sensor-platform/tests/**',
            'sensor-platform/ota/**',
            'docs/release/**',
            'docs/runbooks/**',
            'device-cloud/services/update-service/**'
        )
        FocusTopics = @(
            'HIL test coverage',
            'Release-gate criteria',
            'OTA go/no-go checks',
            'Rollback readiness'
        )
        Goal        = 'Turn implementation changes into an explicit validation matrix, release gate, operator notes, and OTA rollback criteria.'
    }
    @{
        Name        = 'regulatory'
        Branch      = 'ws/regulatory'
        Agent       = 'regulatory-compliance'
        Scope       = @(
            'docs/hardware/**',
            'docs/architecture/**',
            'docs/release/**',
            'docs/protocols/**',
            'sensor-platform/hardware/**',
            'sensor-platform/integrations/**',
            'sensor-platform/tests/**',
            'sensor-platform/ota/**'
        )
        FocusTopics = @(
            'EIRP assumptions',
            'CE and RED impact',
            '6.4 dBi antenna implications',
            'Certification-sensitive protocol and RF decisions'
        )
        Goal        = 'Make certification impact visible early and document the compliance-sensitive decisions before late-stage test surprises.'
    }
)

foreach ($definition in $definitions) {
    Ensure-Worktree -Definition $definition -WorktreeRoot $worktreeRoot
}

$workspaceNamesLiteral = ($definitions | ForEach-Object { "'$($_.Name)'" }) -join ', '

Write-Utf8NoBom -Path (Join-Path $worktreeRoot 'open-selected-claude-workspaces.ps1') -Content @"
param(
    [string[]]`$Names = @($workspaceNamesLiteral)
)

`$valid = @($workspaceNamesLiteral)
`$exe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { 'pwsh' } else { 'powershell' }

foreach (`$name in `$Names) {
    if (`$valid -notcontains `$name) {
        throw "Unknown workspace: `$name"
    }

    `$path = Join-Path `$PSScriptRoot `$name
    if (-not (Test-Path -LiteralPath `$path)) {
        throw "Workspace missing: `$path"
    }

    Start-Process `$exe -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-File', (Join-Path `$path 'open-claude.ps1')
    )
}
"@

Write-Host ""
Write-Host "Claude worktrees created." -ForegroundColor Green
Write-Host "Worktree root: $worktreeRoot" -ForegroundColor Cyan
Write-Host ""

foreach ($definition in $definitions) {
    Write-Host ("- {0}  [{1}]  agent={2}" -f $definition.Name, $definition.Branch, $definition.Agent)
}

Write-Host ""
Write-Host "Open one worktree:" -ForegroundColor Cyan
Write-Host "powershell -ExecutionPolicy Bypass -File `"$worktreeRoot\firmware-mg24\open-claude.ps1`""

Write-Host ""
Write-Host "Open selected worktrees:" -ForegroundColor Cyan
Write-Host "powershell -ExecutionPolicy Bypass -File `"$worktreeRoot\open-selected-claude-workspaces.ps1`" firmware-mg24 zigbee-ha power-rf-hardware"