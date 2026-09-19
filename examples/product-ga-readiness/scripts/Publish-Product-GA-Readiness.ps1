[CmdletBinding()]
param(
    [string] $ReportKitRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string] $WorkbookPath,
    [string] $HtmlPublishDirectory,
    [switch] $Open
)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$workbook = if ($WorkbookPath) {
    [System.IO.Path]::GetFullPath($WorkbookPath)
}
else {
    Join-Path $project 'Product-GA-Readiness-Input.xlsx'
}
$canonical = Join-Path $project 'canonical-report.json'
$configuration = Join-Path $project 'product-ga-readiness.config.json'
$template = Join-Path $project 'templates\microsoft-product-ga-readiness'
$lock = Join-Path $project 'reportkit.lock.json'
$site = Join-Path $project 'generated-site'
$adapter = Join-Path $PSScriptRoot 'excel-to-reportkit.py'
$validateTemplate = Join-Path $ReportKitRoot 'scripts\validate-template'
$buildTemplate = Join-Path $ReportKitRoot 'scripts\build-template'
$validate = Join-Path $ReportKitRoot 'scripts\validate'
$python = (Get-Command python -ErrorAction SilentlyContinue) ??
    (Get-Command python3 -ErrorAction SilentlyContinue)

if (-not $python) {
    throw 'Python 3.10 or later is required.'
}

foreach ($required in @(
    $workbook,
    $adapter,
    $validateTemplate,
    $buildTemplate,
    $validate,
    (Join-Path $template 'template.json'),
    $lock
)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required file not found: $required"
    }
}

& $python.Source -B $adapter --input $workbook --out-dir $project
if ($LASTEXITCODE -ne 0) {
    throw "Excel mapping failed with exit code $LASTEXITCODE."
}

& $python.Source -B $validateTemplate $template
if ($LASTEXITCODE -ne 0) {
    throw "Template validation failed with exit code $LASTEXITCODE."
}

& $python.Source -B $validate $canonical --kind model
if ($LASTEXITCODE -ne 0) {
    throw "Canonical model validation failed with exit code $LASTEXITCODE."
}

$buildArguments = @(
    $buildTemplate,
    '--template', $template,
    '--data', $canonical,
    '--config', $configuration,
    '--lock', $lock,
    '--output', $site
)
if (Test-Path -LiteralPath $site -PathType Container) {
    $buildArguments += '--overwrite'
}
& $python.Source -B @buildArguments
if ($LASTEXITCODE -ne 0) {
    throw "Report build failed with exit code $LASTEXITCODE."
}

& $python.Source -B $validate $site --kind site
if ($LASTEXITCODE -ne 0) {
    throw "Generated-site validation failed with exit code $LASTEXITCODE."
}

$validation = Get-Content -LiteralPath (Join-Path $site 'validation-report.json') -Raw |
    ConvertFrom-Json
if ($validation.status -ne 'passed') {
    throw "Refusing to publish because site validation status is '$($validation.status)'."
}

function Publish-ValidatedFile {
    param(
        [Parameter(Mandatory)]
        [string] $Source,
        [Parameter(Mandatory)]
        [string] $DestinationDirectory,
        [Parameter(Mandatory)]
        [string] $DestinationName
    )

    if (-not (Test-Path -LiteralPath $DestinationDirectory -PathType Container)) {
        throw "Synchronized SharePoint folder not found: $DestinationDirectory"
    }

    $destination = Join-Path $DestinationDirectory $DestinationName
    $transaction = [Guid]::NewGuid().ToString('N')
    $staging = Join-Path $DestinationDirectory ".$DestinationName.reportkit-staging-$transaction"
    $backup = Join-Path $DestinationDirectory ".$DestinationName.reportkit-backup-$transaction"
    $replaced = $false

    try {
        Copy-Item -LiteralPath $Source -Destination $staging
        $sourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
        $stagingHash = (Get-FileHash -LiteralPath $staging -Algorithm SHA256).Hash
        if ($sourceHash -ne $stagingHash) {
            throw "Staged file hash mismatch: $DestinationName"
        }

        if (Test-Path -LiteralPath $destination -PathType Leaf) {
            [System.IO.File]::Replace($staging, $destination, $backup, $true)
            $replaced = $true
        }
        else {
            Move-Item -LiteralPath $staging -Destination $destination
        }

        $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        if ($sourceHash -ne $destinationHash) {
            throw "Published file hash mismatch: $DestinationName"
        }

        if (Test-Path -LiteralPath $backup -PathType Leaf) {
            Remove-Item -LiteralPath $backup -Force
        }
    }
    catch {
        if ($replaced -and (Test-Path -LiteralPath $backup -PathType Leaf)) {
            [System.IO.File]::Replace($backup, $destination, $null, $true)
        }
        elseif (Test-Path -LiteralPath $backup -PathType Leaf) {
            Move-Item -LiteralPath $backup -Destination $destination -Force
        }
        throw
    }
    finally {
        if (Test-Path -LiteralPath $staging -PathType Leaf) {
            Remove-Item -LiteralPath $staging -Force
        }
        if (Test-Path -LiteralPath $backup -PathType Leaf) {
            Remove-Item -LiteralPath $backup -Force
        }
    }
}

if ($HtmlPublishDirectory) {
    Publish-ValidatedFile `
        -Source (Join-Path $site 'index.html') `
        -DestinationDirectory $HtmlPublishDirectory `
        -DestinationName 'index.html'

    Write-Host "Published static report to $HtmlPublishDirectory" -ForegroundColor Green
}

if ($Open) {
    Start-Process -FilePath (Join-Path $site 'index.html')
}

Write-Host "Validated local report: $(Join-Path $site 'index.html')" -ForegroundColor Green
