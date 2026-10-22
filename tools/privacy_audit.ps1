[CmdletBinding()]
param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
Push-Location $RepoRoot
try {
  $tracked = @(git ls-files)
  $sensitiveTracked = @($tracked | Where-Object {
    $_ -match '(?i)(credentials?|secret|token|auth(key)?|beacon(key)?|encrypt(key)?|mifitness-log|wearablelog|\.log$)'
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
