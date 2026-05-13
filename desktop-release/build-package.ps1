param(
  [string]$Version = "0.1.0",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ReleaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ReleaseDir
$OutputDir = Join-Path $RootDir "release-output"
$PackageName = "mjq-handynotes-desktop-v$Version-windows"
$PackageDir = Join-Path $OutputDir $PackageName
$ZipPath = Join-Path $OutputDir "$PackageName.zip"

$ExcludeDirs = @(
  ".git",
  ".test-tmp",
  "test-tmp",
  "__pycache__",
  "frontend\node_modules",
  "node_modules",
  "release-output",
  "cloud-demo"
)

$ExcludeFiles = @(
  ".env",
  "*.log",
  "*.pid",
  "notes.db"
)

function Write-Step($message) {
  Write-Host "[desktop-package] $message" -ForegroundColor Cyan
}

function Should-Exclude($relativePath, $isDirectory) {
  foreach ($dir in $ExcludeDirs) {
    if ($relativePath -eq $dir -or $relativePath.StartsWith("$dir\")) {
      return $true
    }
  }

  if (-not $isDirectory) {
    foreach ($pattern in $ExcludeFiles) {
      if ((Split-Path -Leaf $relativePath) -like $pattern) {
        return $true
      }
    }
  }

  if ($relativePath -eq "data" -or $relativePath.StartsWith("data\")) {
    return $true
  }
  if ($relativePath -eq "raw" -or $relativePath.StartsWith("raw\")) {
    return $true
  }
  if ($relativePath -eq "wiki" -or $relativePath.StartsWith("wiki\")) {
    return $true
  }

  return $false
}

Write-Step "Root: $RootDir"
Write-Step "Package: $ZipPath"

if ($DryRun) {
  Write-Step "Would create clean package directory and zip."
  Write-Step "Would exclude private data, logs, .env, git metadata, caches, and node_modules."
  Write-Step "Dry run complete."
  exit 0
}

if (Test-Path $PackageDir) {
  Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
if (-not (Test-Path $OutputDir)) {
  New-Item -ItemType Directory -Path $OutputDir | Out-Null
}
New-Item -ItemType Directory -Path $PackageDir | Out-Null

$items = Get-ChildItem -Path $RootDir -Recurse -Force
foreach ($item in $items) {
  $relativePath = $item.FullName.Substring($RootDir.Length).TrimStart("\")
  if ($relativePath -eq "") { continue }
  if (Should-Exclude $relativePath $item.PSIsContainer) { continue }

  $target = Join-Path $PackageDir $relativePath
  if ($item.PSIsContainer) {
    if (-not (Test-Path $target)) {
      New-Item -ItemType Directory -Path $target | Out-Null
    }
  } else {
    $targetDir = Split-Path -Parent $target
    if (-not (Test-Path $targetDir)) {
      New-Item -ItemType Directory -Path $targetDir | Out-Null
    }
    Copy-Item -LiteralPath $item.FullName -Destination $target
  }
}

if (Test-Path $ZipPath) {
  Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath
Write-Step "Package created: $ZipPath"

