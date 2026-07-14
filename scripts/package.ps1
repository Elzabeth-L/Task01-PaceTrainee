$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$buildDirectory = Join-Path $projectRoot "build"
$package = Join-Path $buildDirectory "orbit-site.zip"
$handler = Join-Path $projectRoot "app/lambda_function.py"

New-Item -ItemType Directory -Force -Path $buildDirectory | Out-Null
if (Test-Path $package) {
    Remove-Item -LiteralPath $package
}
Compress-Archive -LiteralPath $handler -DestinationPath $package -CompressionLevel Optimal
Write-Output $package
