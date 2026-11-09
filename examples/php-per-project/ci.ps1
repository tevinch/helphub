#requires -Version 7.0
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Run this check on native Windows.' }
$work = Join-Path $env:RUNNER_TEMP ('php-version-check-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory $work)
$artifacts = @(
    @{ Name='php84'; Url='https://downloads.php.net/~windows/releases/php-8.4.27-1-nts-Win32-vs17-x64.zip'; Hash='dbae154a0a89791f36c3d48e68bae797878333e7d6cb5721e74617de59b63ab7' },
    @{ Name='php85'; Url='https://downloads.php.net/~windows/releases/php-8.5.12-1-nts-Win32-vs17-x64.zip'; Hash='2a36a2edcb7a5b9252f638fd5e4cf84d7f6e066092654220dc0b63e5cf4e9723' }
)
foreach ($item in $artifacts) {
    $zip = Join-Path $work ($item.Name + '.zip')
    Invoke-WebRequest $item.Url -OutFile $zip
    if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.Hash) {
        throw "Official PHP archive checksum differs: $($item.Name)"
    }
    Expand-Archive $zip -DestinationPath (Join-Path $work $item.Name)
    Write-Host "Verified $($item.Name) SHA256 $($item.Hash)"
}
$nginxZip = Join-Path $work 'nginx.zip'
Invoke-WebRequest 'https://nginx.org/download/nginx-1.31.8.zip' -OutFile $nginxZip
if ((Get-FileHash $nginxZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'fbb1501009be34655cc238d460714cf20391b639013f4c73859813d7938783fd') {
    throw 'The pinned nginx archive checksum differs.'
}
Expand-Archive $nginxZip -DestinationPath (Join-Path $work 'nginx')
Write-Host ('nginx archive SHA256 ' + (Get-FileHash $nginxZip -Algorithm SHA256).Hash.ToLowerInvariant())
$PSVersionTable.PSVersion.ToString() | Write-Host
& (Join-Path $PSScriptRoot 'verify.ps1') -Php84 (Join-Path $work 'php84') -Php85 (Join-Path $work 'php85') -Nginx (Join-Path $work 'nginx/nginx-1.31.8')
