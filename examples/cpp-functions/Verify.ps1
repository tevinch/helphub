param([Parameter(Mandatory = $true)][string]$CompilerPath)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$exampleRoot = $PSScriptRoot
$compiler = (Resolve-Path -LiteralPath $CompilerPath).Path
$version = (& $compiler --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $version -notmatch '(?<![0-9.])0\.2\.2(?![0-9.])') {
  throw "Expected the Sere 0.2.2 compiler. Actual: $version"
}
$checkRoot = Join-Path ([IO.Path]::GetTempPath()) ('sere-cpp-check-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $checkRoot | Out-Null
$results = [System.Collections.Generic.List[object]]::new()

function Copy-Case([string]$Name) {
  $path = Join-Path $checkRoot $Name
  New-Item -ItemType Directory -Path $path | Out-Null
  foreach ($entry in @('sere.toml', 'libs/native/numbers.cpp', 'libs/native_math.sere', 'src/main.sere')) {
    $destination = Join-Path $path $entry
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $exampleRoot $entry) -Destination $destination
  }
  return $path
}

function Check-Case([string]$Name, [string]$ExpectedFailure, [bool]$DisableNative = $false) {
  $path = Copy-Case $Name
  if ($DisableNative) {
    $manifest = Join-Path $path 'sere.toml'
    $text = [IO.File]::ReadAllText($manifest)
    if ([regex]::Matches($text, [regex]::Escape('native = true')).Count -ne 1) { throw 'Native flag fixture differs' }
    [IO.File]::WriteAllText($manifest, $text.Replace('native = true', 'native = false'))
  }
  if ($ExpectedFailure -eq 'cpp-source-omitted') {
    Remove-Item -LiteralPath (Join-Path $path 'libs/native/numbers.cpp')
  }
  if ($ExpectedFailure -eq 'c-linkage-omitted') {
    $native = Join-Path $path 'libs/native/numbers.cpp'
    $text = [IO.File]::ReadAllText($native)
    if ([regex]::Matches($text, [regex]::Escape('extern "C" ')).Count -ne 2) { throw 'C linkage fixture differs' }
    [IO.File]::WriteAllText($native, $text.Replace('extern "C" ', ''))
  }
  $caseTemp = Join-Path $path 'temp'
  New-Item -ItemType Directory -Path $caseTemp | Out-Null
  [Environment]::SetEnvironmentVariable('TEMP', $caseTemp, 'Process')
  [Environment]::SetEnvironmentVariable('TMP', $caseTemp, 'Process')
  Push-Location $path
  try {
    $buildOutput = (& $compiler build 2>&1 | Out-String)
    $buildExit = $LASTEXITCODE
    Write-Output $buildOutput
    $program = Join-Path $path 'bin/native_math_example.exe'
    if ($ExpectedFailure) {
      if ($buildExit -eq 0 -or (Test-Path -LiteralPath $program)) {
        throw "$Name unexpectedly produced a usable application"
      }
      if ($buildOutput -notmatch '(?is)(undefined symbol|unresolved external).*example_(add|twice)') {
        throw "$Name failed before the intended native-symbol check"
      }
      $results.Add(@{case = $Name; expectedFailure = $ExpectedFailure; nativeSymbolFailure = $true})
      return
    }
    if ($buildExit -ne 0 -or -not (Test-Path -LiteralPath $program)) { throw "$Name did not build the application" }
    $output = (& $program 2>&1 | Out-String).Replace("`r`n", "`n").Trim()
    if ($LASTEXITCODE -ne 0 -or $output -ne "42`n-5`n42") { throw "$Name returned unexpected native results: $output" }
    $results.Add(@{case = $Name; exit = 0; output = $output})
  } finally {
    Pop-Location
  }
}

$projectEnvironmentNames = @('SERE_ACTIVE', 'SERE_PROJECT_ROOT', 'SERE_STDLIB')
$environmentNames = $projectEnvironmentNames + @('TEMP', 'TMP')
$originalEnvironment = @{}
foreach ($name in $environmentNames) {
  $originalEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
try {
  foreach ($name in $projectEnvironmentNames) {
    [Environment]::SetEnvironmentVariable($name, $null, 'Process')
  }
  Check-Case 'without-cpp-source' 'cpp-source-omitted'
  Check-Case 'without-c-linkage' 'c-linkage-omitted'
  Check-Case 'complete' ''
  Check-Case 'complete-again' ''
  Check-Case 'native-false' '' $true
  if ($results.Count -ne 5) { throw 'Not all native workflows executed' }
  @{compiler = $version; platform = 'Windows x64'; results = $results} | ConvertTo-Json -Depth 5
} finally {
  try {
    foreach ($name in $environmentNames) {
      [Environment]::SetEnvironmentVariable($name, $originalEnvironment[$name], 'Process')
    }
  } finally {
    Remove-Item -LiteralPath $checkRoot -Recurse -Force
  }
}
