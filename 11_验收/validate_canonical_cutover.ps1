param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$failures = [System.Collections.Generic.List[string]]::new()

function Require-Path {
    param([string]$RelativePath)
    if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot $RelativePath) -PathType Leaf)) {
        $failures.Add("missing path: $RelativePath")
    }
}

function Require-Text {
    param([string]$RelativePath, [string]$Pattern)
    [string]$filePath = [System.IO.Path]::Combine([string]$RepositoryRoot, [string]$RelativePath)
    $content = [System.IO.File]::ReadAllText($filePath, [System.Text.Encoding]::UTF8)
    if ($content -notmatch $Pattern) {
        $failures.Add("missing pattern [$Pattern] in $RelativePath")
    }
}

function Get-DocumentContent {
    param([string]$MetadataPattern)
    $matches = @(Get-ChildItem -LiteralPath $RepositoryRoot -Recurse -File -Filter *.md | ForEach-Object {
        $content = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
        if ($content -match $MetadataPattern) {
            [pscustomobject]@{ Path = $_.FullName; Content = $content }
        }
    })
    if ($matches.Count -ne 1) {
        $failures.Add("expected one document matching metadata: $MetadataPattern; found $($matches.Count)")
        return ''
    }
    return $matches[0].Content
}

function Require-Content {
    param([string]$Label, [string]$Content, [string]$Pattern)
    if ($Content -notmatch $Pattern) {
        $failures.Add("missing pattern [$Pattern] in $Label")
    }
}

function Get-LegacyPolicyDefinition {
    param([string]$Root)

    $indexPath = Join-Path $Root 'PROJECT_INDEX.yaml'
    $authorityPath = (Get-ChildItem -LiteralPath $Root -Recurse -File -Filter 'source_authority.yaml' | Select-Object -First 1).FullName
    if ([string]::IsNullOrWhiteSpace($authorityPath)) {
        $failures.Add('could not locate source_authority.yaml')
        return [pscustomobject]@{ Pattern = '(?!)'; Patterns = @() }
    }
    $indexLines = [System.IO.File]::ReadAllLines($indexPath, [System.Text.Encoding]::UTF8)
    $authorityLines = [System.IO.File]::ReadAllLines($authorityPath, [System.Text.Encoding]::UTF8)
    $projectPatterns = @()
    $authorityPatterns = @()
    $collectProject = $false
    foreach ($line in $indexLines) {
        if ($line -match '^legacy_policy:') { $collectProject = $false; continue }
        if ($line -match '^  patterns:') { $collectProject = $true; continue }
        if ($collectProject -and $line -match '^    -\s+["'']?(.+?)["'']?\s*$') { $projectPatterns += $Matches[1]; continue }
        if ($collectProject -and $line -match '^\S') { $collectProject = $false }
    }
    $collectAuthority = $false
    foreach ($line in $authorityLines) {
        if ($line -match '^reject_as_active:') { $collectAuthority = $true; continue }
        if ($collectAuthority -and $line -match '^  -\s+["'']?(.+?)["'']?\s*$') { $authorityPatterns += $Matches[1]; continue }
        if ($collectAuthority -and $line -match '^\S') { $collectAuthority = $false }
    }
    $projectPatterns = @($projectPatterns | Sort-Object -Unique)
    $authorityPatterns = @($authorityPatterns | Sort-Object -Unique)
    if ((Compare-Object $projectPatterns $authorityPatterns).Count -ne 0) {
        $failures.Add('PROJECT_INDEX legacy_policy.patterns and source_authority.reject_as_active disagree')
    }
    if ($projectPatterns.Count -eq 0) {
        $failures.Add('PROJECT_INDEX legacy_policy.patterns is empty')
        return [pscustomobject]@{ Pattern = '(?!)'; Patterns = @() }
    }
    $regexParts = $projectPatterns | ForEach-Object { [regex]::Escape($_).Replace('\*', '.*') }
    return [pscustomobject]@{ Pattern = '(?i)(?:' + ($regexParts -join '|') + ')'; Patterns = $projectPatterns }
}

function Get-LegacyReferenceClassification {
    param([string]$Text, [string]$Scope = 'document', [string]$LegacyPattern)

    if ($Text -notmatch $LegacyPattern) { return 'pass_no_reference' }
    if ($Scope -eq 'machine_route') { return 'fail_active' }

    $activePattern = '(?i)(must\s+read|current\s+basis|canonical|authoritative|active\s+source|fallback|effective_sources|\u5fc5\u987b\u8bfb\u53d6|\u5f53\u524d\u4f9d\u636e|\u9ed8\u8ba4(?:\u8bfb\u53d6|\u4f7f\u7528)|\u4ee5\u540e\u4f7f\u7528)'
    $referenceLines = @($Text -split "`r?`n" | Where-Object { $_ -match $LegacyPattern })
    $referenceText = [string]::Join("`n", $referenceLines)
    $explicitRejectionPattern = '(?i)(?:must\s+not|do\s+not|not\s+be\s+used|\u4e0d\u5f97|\u7981\u6b62|\u4e0d\u518d).{0,120}(?:active|canonical|rule|\u6d3b\u52a8|\u4e3b\u6863|\u89c4\u5219)'
    $explicitMigrationPattern = '(?i)(?:\u5df2(?:\u7ecf)?\u8fc1\u79fb(?:\u8fdb\u5165|\u81f3|\u5230)|migrat(?:ed|ion).{0,120}(?:into|to)|superseded\s+by|replaced\s+by|\u5df2\u88ab\u53d6\u4ee3).{0,120}(?:current|github|project_index|\u5f53\u524d|\u73b0\u884c|AI\u7535\u5f71\u7cfb\u7edf)'
    # Issue #6: a legacy locator may be followed by a narrowly scoped identity
    # statement saying it is historical migration evidence and explicitly NOT
    # current canonical.  This is historical provenance, not an allow-list.
    # The legacy-bearing line itself is still checked first for active language,
    # so "must read old file" remains fail_active even if a nearby note says it
    # is historical.
    $explicitHistoricalIdentityPattern = '(?i)(?:\u5386\u53f2(?:\u8fc1\u79fb)?\u8bc1\u636e|\u5386\u53f2\u8bb0\u5f55|historical(?:\s+migration)?\s+evidence|legacy\s+evidence).{0,80}(?:\u4e0d\u662f|\u5e76\u975e|\u4e0d\u5c5e\u4e8e|is\s+not|not\s+(?:the\s+)?current).{0,40}(?:\u5f53\u524d|current)?\s*(?:canonical|\u4e3b\u6863|authority|\u89c4\u5219\u6e90)'
    $isExplicitHistorical = (($Text -match $explicitRejectionPattern) -or ($Text -match $explicitMigrationPattern) -or ($Text -match $explicitHistoricalIdentityPattern))
    # A clear historical statement may explain an ambiguous locator on its
    # immediate next non-empty line.  Positive activity on the legacy-bearing
    # line still wins, preventing contextual history from laundering an active
    # route or "must read" instruction.
    if ($referenceText -match $activePattern) { return 'fail_active' }
    if ($isExplicitHistorical) { return 'pass_historical' }
    return 'fail_ambiguous'
}

function Test-LegacyAuthorityReferences {
    param([string]$Root, [string]$LegacyPattern)

    $strictMachineFiles = @('PROJECT_INDEX.yaml', 'read_sets.yaml', 'write_routes.yaml', 'director_route_index.yaml', 'CHATGPT_PROJECT_INSTRUCTION.md')
    $files = Get-ChildItem -LiteralPath $Root -Recurse -File | Where-Object { $_.Extension -in @('.md', '.yaml') }
    foreach ($file in $files) {
        if ($file.Name -eq 'legacy_authority_regression_cases.yaml') { continue }
        $lines = [System.IO.File]::ReadAllLines($file.FullName, [System.Text.Encoding]::UTF8)
        $section = ''
        for ($i = 0; $i -lt $lines.Count; $i++) {
            $line = $lines[$i]
            if ($line -match '^([A-Za-z_][A-Za-z0-9_]*):') { $section = $Matches[1] }
            if ($line -notmatch $LegacyPattern) { continue }
            $relative = $file.FullName.Substring($Root.Length).TrimStart('\', '/')
            # Machine-readable route files are strict.  The only exception is the
            # explicit deny-list itself: it documents retired names in order to
            # reject them, rather than selecting them as a source.
            $isExplicitRejectList = (($file.Name -eq 'PROJECT_INDEX.yaml') -and ($section -eq 'legacy_policy')) -or
                (($file.Name -eq 'source_authority.yaml') -and ($section -eq 'reject_as_active'))
            $lineClassification = Get-LegacyReferenceClassification -Text $line -LegacyPattern $LegacyPattern
            if ((($strictMachineFiles -contains $file.Name) -and (-not $isExplicitRejectList) -and ($lineClassification -ne 'pass_historical')) -or (($file.Name -eq 'source_authority.yaml') -and ($section -ne 'reject_as_active'))) {
                $failures.Add("active legacy authority reference: ${relative}:$($i + 1): $line")
                continue
            }
            if ($isExplicitRejectList) { continue }
            $classification = $lineClassification
            # Only an ambiguous reference may consult its immediate next
            # non-empty line. Earlier lines are intentionally excluded: an
            # unrelated historical note cannot convert an active pointer into
            # a permitted history mention.
            if ($classification -eq 'fail_ambiguous') {
                $nextNonEmpty = ''
                for ($next = $i + 1; ($next -lt $lines.Count) -and ($next -le ($i + 6)); $next++) {
                    if (-not [string]::IsNullOrWhiteSpace($lines[$next])) { $nextNonEmpty = $lines[$next]; break }
                }
                if ($nextNonEmpty) {
                    $classification = Get-LegacyReferenceClassification -Text ($line + "`n" + $nextNonEmpty) -LegacyPattern $LegacyPattern
                }
            }
            if ($classification -ne 'pass_historical') {
                $failures.Add("$classification legacy reference requires review: ${relative}:$($i + 1): $line")
            }
        }
    }
}

function Test-LegacyAuthorityGoldenCases {
    param([string]$Root, [string]$LegacyPattern)

    $caseFile = Get-ChildItem -LiteralPath $Root -Recurse -File -Filter 'legacy_authority_regression_cases.yaml'
    if ($caseFile.Count -ne 1) {
        $failures.Add("expected one legacy_authority_regression_cases.yaml; found $($caseFile.Count)")
        return
    }
    $caseJson = & python -c "import json,sys,yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1], encoding='utf-8')), ensure_ascii=True))" $caseFile.FullName
    if ($LASTEXITCODE -ne 0) {
        $failures.Add('could not parse legacy authority regression cases')
        return
    }
    foreach ($case in (($caseJson | ConvertFrom-Json).cases)) {
        $actual = Get-LegacyReferenceClassification -Text $case.sample -Scope $case.scope -LegacyPattern $LegacyPattern
        if ($actual -ne $case.expected) {
            $failures.Add("legacy authority golden case failed: $($case.id); expected $($case.expected); got $actual")
        }
    }
}

$indexPath = Join-Path $RepositoryRoot 'PROJECT_INDEX.yaml'
$index = Get-Content -Raw -Encoding utf8 -LiteralPath $indexPath
$legacyPolicy = Get-LegacyPolicyDefinition -Root $RepositoryRoot
if ($index -notmatch '(?m)^status: full_github_cutover_verified$') {
    $failures.Add('PROJECT_INDEX status is not full_github_cutover_verified')
}

$canonicalPaths = [regex]::Matches($index, '(?m)^  [A-Za-z_]+: ([^#\r\n]+)$') |
    ForEach-Object { $_.Groups[1].Value.Trim() } |
    Where-Object { $_ -match '\.(md|yaml)$' } |
    Select-Object -Unique
foreach ($relativePath in $canonicalPaths) {
    Require-Path $relativePath
}

foreach ($relativePath in ($canonicalPaths | Where-Object { $_ -match '^(01_|02_|05_)' })) {
    if ($index -notmatch [regex]::Escape(($relativePath + ': github_verified'))) {
        $failures.Add("source authority not github_verified: $relativePath")
    }
}

Test-LegacyAuthorityReferences -Root $RepositoryRoot -LegacyPattern $legacyPolicy.Pattern
Test-LegacyAuthorityGoldenCases -Root $RepositoryRoot -LegacyPattern $legacyPolicy.Pattern

Require-Text -RelativePath 'MIGRATION_STATUS.md' -Pattern 'FULL_GITHUB_CUTOVER / VERIFIED'
$handoffPath = Join-Path $RepositoryRoot 'AI_HANDOFF.yaml'
if (-not (Test-Path -LiteralPath $handoffPath -PathType Leaf)) {
    $failures.Add('missing AI_HANDOFF.yaml')
} else {
    & python -c "import sys,yaml; yaml.safe_load(open(sys.argv[1], encoding='utf-8')); print('PASS AI_HANDOFF YAML parse')" $handoffPath
    if ($LASTEXITCODE -ne 0) {
        $failures.Add('AI_HANDOFF.yaml failed YAML parser validation')
    }
}
$map = Get-DocumentContent -MetadataPattern 'document_id: EUSTIA-PROJECT-MAP'
$assets = Get-DocumentContent -MetadataPattern 'document_id: EUSTIA-VISUAL-ASSET-REGISTRY'
$screenplay = Get-DocumentContent -MetadataPattern 'document_id: EUSTIA-CURRENT-ADAPTED-SCRIPT'
$system = Get-DocumentContent -MetadataPattern 'system_id: DIRECTOR-CINEMA-SYSTEM'
$memory = Get-DocumentContent -MetadataPattern 'document_id: EUSTIA-PROJECT-MEMORY'
Require-Content -Label 'map' -Content $map -Pattern 'SCN-CHURCH-BELLTOWER-SOUTH-001'
Require-Content -Label 'map' -Content $map -Pattern 'SCN-CHECKPOINT-MIDDLE-GATE-001'
Require-Content -Label 'map' -Content $map -Pattern 'SCN-BRIDGE-SOUTH-FACE-001'
Require-Content -Label 'assets' -Content $assets -Pattern 'SCN-CHURCH-BELLTOWER-LEFT-001'
Require-Content -Label 'assets' -Content $assets -Pattern 'SCN-CHURCH-BELLTOWER-RIGHT-001'
Require-Content -Label 'screenplay' -Content $screenplay -Pattern 'CONFIRMED / CURRENT_PRODUCTION'
Require-Content -Label 'screenplay' -Content $screenplay -Pattern 'target_confirmed: false'
Require-Content -Label 'system' -Content $system -Pattern 'Character Autonomous Life Continuity'
Require-Content -Label 'system' -Content $system -Pattern 'Camera-Off.*Swap.*Omniscience.*Optimizer'
Require-Content -Label 'system' -Content $system -Pattern 'timecode'
Require-Content -Label 'system' -Content $system -Pattern 'six freedom|six.*degree|camera height'
Require-Content -Label 'system' -Content $system -Pattern 'DIRECTOR-FULL-OUTPUT-001'
Require-Content -Label 'project_memory' -Content $memory -Pattern 'AIP-001'
Require-Content -Label 'project_memory' -Content $memory -Pattern 'Seedance'
$regressionCasesFile = Get-ChildItem -LiteralPath $RepositoryRoot -Recurse -File -Filter 'director_regression_cases.yaml'
if ($regressionCasesFile.Count -ne 1) {
    $failures.Add("expected one director_regression_cases.yaml; found $($regressionCasesFile.Count)")
} else {
    $regressionCases = [System.IO.File]::ReadAllText($regressionCasesFile.FullName, [System.Text.Encoding]::UTF8)
    Require-Content -Label 'regression_cases' -Content $regressionCases -Pattern 'REG-DIRECTOR-FULL-OUTPUT-001'
}
$writeRoutesFile = Get-ChildItem -LiteralPath $RepositoryRoot -Recurse -File -Filter 'write_routes.yaml'
if ($writeRoutesFile.Count -ne 1) {
    $failures.Add("expected one write_routes.yaml; found $($writeRoutesFile.Count)")
} else {
    $writeRoutes = [System.IO.File]::ReadAllText($writeRoutesFile.FullName, [System.Text.Encoding]::UTF8)
    Require-Content -Label 'write_routes' -Content $writeRoutes -Pattern 'scene_topology_map_movement: .*00_'
}

$unknownFile = Get-ChildItem -LiteralPath $RepositoryRoot -Recurse -File -Filter 'UNKNOWN_REGISTRY.yaml'
if ($unknownFile.Count -ne 1) {
    $failures.Add("expected one UNKNOWN_REGISTRY.yaml; found $($unknownFile.Count)")
    $unknown = ''
} else {
    $unknown = [System.IO.File]::ReadAllText($unknownFile.FullName, [System.Text.Encoding]::UTF8)
}
foreach ($id in @('U-MIG-001', 'U-MIG-002', 'U-SCENE-001')) {
    if ($unknown -notmatch "(?s)$id.*?status: resolved") {
        $failures.Add("migration unknown remains open: $id")
    }
}
if ($unknown -notmatch '(?s)U-ASSET-RETRIEVAL-001.*?status: open') {
    $failures.Add('asset retrieval unknown is missing or not open')
}
if ([regex]::Matches($unknown, 'U-ASSET-RETRIEVAL-001').Count -ne 1) {
    $failures.Add('asset retrieval unknown must have exactly one registry entry')
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Output "PASS canonical existence, source authority, handoff YAML, map, asset, screenplay, CALC, director full output, write routes, and migration unknown closure"
