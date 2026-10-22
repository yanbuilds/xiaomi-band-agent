param(
    [string]$Serial = "192.168.10.144:38141",
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$apk = Join-Path $PSScriptRoot "..\outputs\band9pro-mvp\gadgetbridge-spp-debug.apk"
$expected = "2e75a7dba77514902e8a2a3dba44236dd3ce855a13f0add6a430d3f6fcc59e0c"

if (-not (Test-Path -LiteralPath $apk)) { throw "APK not found: $apk" }
$actual = (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "APK hash mismatch; refusing to continue" }

$state = (& adb -s $Serial get-state 2>$null).Trim()
if ($state -ne "device") { throw "ADB device is not ready: $Serial" }
$lock = (& adb -s $Serial shell dumpsys window 2>$null | Select-String "mDreamingLockscreen=true")
if ($lock) { throw "Phone is locked; unlock it visibly before installation" }

Write-Host "Preflight passed for $Serial"
Write-Host "APK SHA-256: $actual"
if (-not $Install) {
    Write-Host "Dry-run only. Re-run with -Install to install the debug APK."
    exit 0
}

& adb -s $Serial install -r --no-streaming $apk
if ($LASTEXITCODE -ne 0) { throw "ADB installation failed" }
Write-Host "Installed successfully; no app data was cleared."
