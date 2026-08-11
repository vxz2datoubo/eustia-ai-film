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

$activeFiles = Get-ChildItem -LiteralPath $RepositoryRoot -Recurse -File |
    Where-Object { $_.Extension -in @('.md', '.yaml') -and $_.Name -ne 'AI_HANDOFF.yaml' }
foreach ($legacyPattern in @('file_library_until_verified_migration', '_v1\.', '_v2\.', 'FINAL.*canonical', 'FINAL.*active')) {
    $hits = $activeFiles | Select-String -Pattern $legacyPattern
    if ($hits) {
        $failures.Add("active legacy authority reference: $legacyPattern")
    }
}

Require-Text -RelativePath 'MIGRATION_STATUS.md' -Pattern 'FULL_GITHUB_CUTOVER / VERIFIED'
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
Require-Content -Label 'project_memory' -Content $memory -Pattern 'AIP-001'
Require-Content -Label 'project_memory' -Content $memory -Pattern 'Seedance'
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

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Output "PASS canonical existence, source authority, legacy rejection, map, asset, screenplay, CALC, write routes, and migration unknown closure"
