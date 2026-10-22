param(
    [string]$Serial = "192.168.10.144:38141",
    [switch]$Pull
)

$ErrorActionPreference = "Stop"
$roots = @(
    "/sdcard/Android/data/com.mi.health/files/log",
    "/sdcard/Android/data/com.xiaomi.wearable/files/log"
)
$out = Join-Path $PSScriptRoot "..\work\mifitness-log-extract"

$state = (& adb -s $Serial get-state 2>$null).Trim()
if ($state -ne "device") { throw "ADB device is not ready: $Serial" }
if (-not $Pull) {
    Write-Host "Dry-run: checking shared Mi Fitness log directories only."
    foreach ($root in $roots) {
        $items = & adb -s $Serial shell "find '$root' -maxdepth 1 -type f 2>/dev/null"
        if ($items) { Write-Host "$root : $($items.Count) files" }
    }
    Write-Host "Re-run with -Pull to copy logs into the ignored work/ directory."
    exit 0
}

New-Item -ItemType Directory -Force -Path $out | Out-Null
foreach ($root in $roots) {
    $name = ($root -split '/')[-3]
    $dest = Join-Path $out $name
    $items = & adb -s $Serial shell "find '$root' -maxdepth 1 -type f 2>/dev/null"
    if ($items) {
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        & adb -s $Serial pull $root $dest | Out-Null
        Write-Host "Copied $($items.Count) files from $name; raw content stays local."
    }
}
Write-Host "Done. No log contents, credentials, or device identifiers were printed."
