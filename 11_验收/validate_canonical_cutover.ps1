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

function Get-LegacyReferenceClassification {
    param([string]$Text, [string]$Scope = 'document')

    # The named retired outline is legacy even when an historical note omits its
    # version suffix; generic versioned Markdown references remain covered too.
    $legacyPattern = '(?i)(?:AI\u7535\u5F71\u5316\u7CFB\u7EDF\u603B\u7EB2(?:_v[0-9]+(?:\.[0-9]+)*)?\.md|_v[0-9]+(?:\.[0-9]+)*\.md|_V[0-9]+(?:\.[0-9]+)?(?:_[^\s`"'']+)?\.md)'
    if ($Text -notmatch $legacyPattern) { return 'pass_no_reference' }
    if ($Scope -eq 'machine_route') { return 'fail_active' }

    $historyPattern = '(?i)(deprecated|superseded|legacy.*(?:only|evidence)|migrat(?:ed|ion)|replaced|reject_as_active|\u5e9f\u5f03|\u5386\u53f2|\u8fc1\u79fb|\u4e0d\u5f97|\u7981\u6b62|\u4e0d\u518d|\u53d6\u4ee3)'
    $activePattern = '(?i)(must\s+read|current\s+basis|canonical|authoritative|active\s+source|fallback|effective_sources|\u5fc5\u987b\u8bfb\u53d6|\u5f53\u524d\u4f9d\u636e|\u6d3b\u52a8\u89c4\u5219|\u9ed8\u8ba4(?:\u8bfb\u53d6|\u4f7f\u7528)|\u4ee5\u540e\u4f7f\u7528)'
    if ($Text -match $historyPattern) { return 'pass_historical' }
    if ($Text -match $activePattern) { return 'fail_active' }
    return 'fail_ambiguous'
}

function Test-LegacyAuthorityReferences {
    param([string]$Root)

    $legacyPattern = '(?i)(?:AI\u7535\u5F71\u5316\u7CFB\u7EDF\u603B\u7EB2(?:_v[0-9]+(?:\.[0-9]+)*)?\.md|_v[0-9]+(?:\.[0-9]+)*\.md|_V[0-9]+(?:\.[0-9]+)?(?:_[^\s`"'']+)?\.md)'
    $strictMachineFiles = @('PROJECT_INDEX.yaml', 'read_sets.yaml', 'write_routes.yaml', 'director_route_index.yaml', 'CHATGPT_PROJECT_INSTRUCTION.md')
    $files = Get-ChildItem -LiteralPath $Root -Recurse -File | Where-Object { $_.Extension -in @('.md', '.yaml') }
    foreach ($file in $files) {
        if ($file.Name -eq 'legacy_authority_regression_cases.yaml') { continue }
        $lines = [System.IO.File]::ReadAllLines($file.FullName, [System.Text.Encoding]::UTF8)
        $section = ''
        for ($i = 0; $i -lt $lines.Count; $i++) {
            $line = $lines[$i]
            if ($line -match '^([A-Za-z_][A-Za-z0-9_]*):') { $section = $Matches[1] }
            if ($line -notmatch $legacyPattern) { continue }
            $relative = $file.FullName.Substring($Root.Length).TrimStart('\', '/')
            if (($strictMachineFiles -contains $file.Name) -or (($file.Name -eq 'source_authority.yaml') -and ($section -ne 'reject_as_active'))) {
                $failures.Add("active legacy authority reference: ${relative}:$($i + 1): $line")
                continue
            }
            if (($file.Name -eq 'source_authority.yaml') -and ($section -eq 'reject_as_active')) { continue }
            $from = [Math]::Max(0, $i - 10)
            $to = [Math]::Min($lines.Count - 1, $i + 2)
            $context = [string]::Join("`n", $lines[$from..$to])
            $classification = Get-LegacyReferenceClassification -Text $context
            if ($classification -ne 'pass_historical') {
                $failures.Add("$classification legacy reference requires review: ${relative}:$($i + 1): $line")
            }
        }
    }
}

function Test-LegacyAuthorityGoldenCases {
    param([string]$Root)

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
        $actual = Get-LegacyReferenceClassification -Text $case.sample -Scope $case.scope
        if ($actual -ne $case.expected) {
            $failures.Add("legacy authority golden case failed: $($case.id); expected $($case.expected); got $actual")
        }
    }
}

$indexPath = Join-Path $RepositoryRoot 'PROJECT_INDEX.yaml'
$index = Get-Content -Raw -Encoding utf8 -LiteralPath $indexPath
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

Test-LegacyAuthorityReferences -Root $RepositoryRoot
Test-LegacyAuthorityGoldenCases -Root $RepositoryRoot

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
