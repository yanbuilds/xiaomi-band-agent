[CmdletBinding()]
param(
  [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$scriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($scriptPath)) { $scriptPath = $PSCommandPath }
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path (Split-Path -Parent $scriptPath) '..')).Path
}
Push-Location $RepoRoot
try {
  $tracked = @(git ls-files)
  $sensitiveTracked = @($tracked | Where-Object {
    # Documentation and source names may mention credentials safely. Flag only
    # likely secret-bearing artifacts or raw log files.
    $_ -match '(?i)(^|[/\\])(credentials?(\.local)?|.*\.(log|key|pem|p12|pfx)$|mifitness-log-extract|wearablelog)([/\\]|$)'
  })
  $rawDirs = @(
    (Join-Path $RepoRoot 'work/mifitness-log-extract'),
    (Join-Path $RepoRoot 'work/wearablelog')
  ) | Where-Object { Test-Path -LiteralPath $_ }
  $ignoredCredential = Test-Path -LiteralPath (Join-Path $RepoRoot 'work/mihealth/credentials.local')

  $result = [ordered]@{
    read_only = $true
    tracked_sensitive_path_count = $sensitiveTracked.Count
    raw_log_directory_count = $rawDirs.Count
    local_credential_file_present = $ignoredCredential
    checks = @(
      'No secret values are read or printed.'
      'Only Git path names and directory existence are inspected.'
    )
  }
  if ($sensitiveTracked.Count -gt 0) { $result.tracked_sensitive_paths = $sensitiveTracked }
  if ($rawDirs.Count -gt 0) { $result.raw_log_directories = $rawDirs }
  $result | ConvertTo-Json -Depth 4
  if ($sensitiveTracked.Count -gt 0 -or $rawDirs.Count -gt 0) { exit 2 }
}
finally {
  Pop-Location
}
