#requires -Version 7.0
param(
    [Parameter(Mandatory)][string]$Php84,
    [Parameter(Mandatory)][string]$Php85,
    [Parameter(Mandatory)][string]$Nginx
)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This integration check requires native Windows.' }

$Php84 = (Resolve-Path $Php84).Path
$Php85 = (Resolve-Path $Php85).Path
$Nginx = (Resolve-Path $Nginx).Path
$root = Join-Path ([IO.Path]::GetTempPath()) ('PHP projects ' + [guid]::NewGuid().ToString('N'))
$prefix = $root.Replace('\', '/') + '/'
$children = [Collections.Generic.List[Diagnostics.Process]]::new()
$nginxMaster = $null
$http = [Net.Http.HttpClient]::new()
$http.Timeout = [TimeSpan]::FromSeconds(5)

function Start-Program([string]$Exe, [string[]]$Arguments, [string]$Directory) {
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Exe
    $start.UseShellExecute = $false
    $start.WorkingDirectory = $Directory
    foreach ($item in $Arguments) { [void]$start.ArgumentList.Add($item) }
    $process = [Diagnostics.Process]::Start($start)
    $children.Add($process)
    return $process
}
function Request([int]$Port, [string]$Path = '/index.php?value=kept', [string]$Body = 'request body') {
    $content = [Net.Http.StringContent]::new($Body)
    try {
        $response = $http.PostAsync("http://127.0.0.1:$Port$Path", $content).GetAwaiter().GetResult()
        try { return @{ Status = [int]$response.StatusCode; Body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() } }
        finally { $response.Dispose() }
    } finally { $content.Dispose() }
}
function Check-Project([int]$Port, [string]$Version, [string]$Marker, [string]$Memory, [string]$Ini) {
    $reply = Request $Port
    if ($reply.Status -ne 200) { throw "Project on $Port returned HTTP $($reply.Status): $($reply.Body)" }
    $data = $reply.Body | ConvertFrom-Json
    if (-not $data.version.StartsWith($Version) -or $data.sapi -ne 'cgi-fcgi' -or
        $data.project -ne $Marker -or $data.memory -ne $Memory -or
        $data.forceRedirect -ne '1' -or $data.value -ne 'kept' -or $data.body -ne 'request body' -or
        $data.ini -ne $Ini) { throw "Wrong project/runtime/configuration on $Port`: $($reply.Body)" }
    Write-Host $reply.Body
}
function Wait-Project([int]$Port, [string]$Version, [string]$Marker, [string]$Memory, [string]$Ini) {
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    do {
        try { Check-Project $Port $Version $Marker $Memory $Ini; return }
        catch {
            if ([DateTime]::UtcNow -ge $deadline) { throw }
            Start-Sleep -Milliseconds 100
        }
    } while ($true)
}

try {
    foreach ($directory in @('conf', 'logs', 'project84', 'project85')) {
        [void](New-Item -ItemType Directory -Path (Join-Path $root $directory) -Force)
    }
    foreach ($port in @(9084, 9085, 18084, 18085)) {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port)
        try { $listener.Start() } finally { $listener.Stop() }
    }
    $source = @'
<?php
header('Content-Type: application/json');
echo json_encode([
    'version' => PHP_VERSION, 'sapi' => PHP_SAPI,
    'project' => basename(__DIR__), 'memory' => ini_get('memory_limit'),
    'forceRedirect' => ini_get('cgi.force_redirect'),
    'ini' => php_ini_loaded_file(), 'value' => $_GET['value'] ?? null,
    'body' => file_get_contents('php://input'),
]);
'@
    foreach ($item in @(@{ Folder=$Php84; Name='84'; Memory='128M' }, @{ Folder=$Php85; Name='85'; Memory='192M' })) {
        $version = & (Join-Path $item.Folder 'php.exe') -n -r 'echo PHP_VERSION;'
        if ($LASTEXITCODE -ne 0 -or -not $version.StartsWith('8.' + $item.Name.Substring(1) + '.')) {
            throw "Expected PHP 8.$($item.Name.Substring(1)) in $($item.Folder), got $version"
        }
        $ini = Join-Path $root ("php$($item.Name).ini")
        "cgi.force_redirect=1`ncgi.fix_pathinfo=0`nmemory_limit=$($item.Memory)`n" | Set-Content $ini -Encoding utf8NoBOM
        $source | Set-Content (Join-Path $root "project$($item.Name)/index.php") -Encoding utf8NoBOM
        # -c selects this version's INI; php-cgi owns its distinct loopback socket.
        $process = Start-Program (Join-Path $item.Folder 'php-cgi.exe') @('-c', $ini, '-b', "127.0.0.1:90$($item.Name)") $item.Folder
        if ($item.Name -eq '84') { $first = $process }
    }
    $nginxDirectory = $Nginx.Replace('\', '/')
    $config = @"
worker_processes 1;
pid logs/nginx.pid;
error_log logs/error.log;
events { worker_connections 128; }
http {
    access_log logs/access.log;
    server {
        listen 127.0.0.1:18084;
        root "${prefix}project84";
        location / { try_files `$uri `$uri/ /index.php`$is_args`$args; }
        location ~ \.php`$ {
            try_files `$uri =404;
            include "$nginxDirectory/conf/fastcgi_params";
            fastcgi_param SCRIPT_FILENAME `$document_root`$fastcgi_script_name;
            fastcgi_pass 127.0.0.1:9084;
        }
    }
    server {
        listen 127.0.0.1:18085;
        root "${prefix}project85";
        location / { try_files `$uri `$uri/ /index.php`$is_args`$args; }
        location ~ \.php`$ {
            try_files `$uri =404;
            include "$nginxDirectory/conf/fastcgi_params";
            fastcgi_param SCRIPT_FILENAME `$document_root`$fastcgi_script_name;
            fastcgi_pass 127.0.0.1:9085;
        }
    }
}
"@
    $config | Set-Content (Join-Path $root 'conf/nginx.conf') -Encoding utf8NoBOM
    $exe = Join-Path $Nginx 'nginx.exe'
    & $exe -v
    if ($LASTEXITCODE -ne 0) { throw 'nginx executable check failed.' }
    & $exe -p $prefix -c conf/nginx.conf -t
    if ($LASTEXITCODE -ne 0) { throw 'nginx configuration validation failed.' }
    $launch = Start-Program $exe @('-p', $prefix, '-c', 'conf/nginx.conf') $root
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path (Join-Path $root 'logs/nginx.pid'))) {
        if ([DateTime]::UtcNow -gt $deadline) { throw 'nginx did not create its test PID file.' }
        Start-Sleep -Milliseconds 100
    }
    $nginxMaster = Get-Process -Id ([int](Get-Content (Join-Path $root 'logs/nginx.pid')))
    Wait-Project 18084 '8.4.' 'project84' '128M' (Join-Path $root 'php84.ini')
    Wait-Project 18085 '8.5.' 'project85' '192M' (Join-Path $root 'php85.ini')
    foreach ($round in 1..3) {
        Check-Project 18084 '8.4.' 'project84' '128M' (Join-Path $root 'php84.ini')
        Check-Project 18085 '8.5.' 'project85' '192M' (Join-Path $root 'php85.ini')
    }
    if ($first.HasExited) { throw 'The first CGI process did not remain alive concurrently.' }
    ($source.Replace("basename(__DIR__)", "'edited84'")) | Set-Content (Join-Path $root 'project84/index.php') -Encoding utf8NoBOM
    & $exe -p $prefix -c conf/nginx.conf -s reload
    if ($LASTEXITCODE -ne 0) { throw 'nginx reload failed.' }
    Check-Project 18084 '8.4.' 'edited84' '128M' (Join-Path $root 'php84.ini')
    Check-Project 18085 '8.5.' 'project85' '192M' (Join-Path $root 'php85.ini')
    if ((Request 18084 '/missing.php').Status -ne 404) { throw 'Missing PHP file was not rejected with HTTP404.' }
    $first.Kill(); $first.WaitForExit()
    if ((Request 18084).Status -ne 502) { throw 'Stopped backend did not yield HTTP502.' }
    Check-Project 18085 '8.5.' 'project85' '192M' (Join-Path $root 'php85.ini')
    $restart = Start-Program (Join-Path $Php84 'php-cgi.exe') @('-c', (Join-Path $root 'php84.ini'), '-b', '127.0.0.1:9084') $Php84
    Wait-Project 18084 '8.4.' 'edited84' '128M' (Join-Path $root 'php84.ini')
    Check-Project 18085 '8.5.' 'project85' '192M' (Join-Path $root 'php85.ini')
    Write-Host 'PASS: native Windows concurrent CGI versions, per-project config/content, repeated requests, edit/reload, missing-file rejection, independent failure and recovery.'
} finally {
    $http.Dispose()
    if ($nginxMaster) {
        & (Join-Path $Nginx 'nginx.exe') -p $prefix -c conf/nginx.conf -s quit
        if (-not $nginxMaster.WaitForExit(5000)) { $nginxMaster.Kill($true) }
    }
    foreach ($child in $children) {
        if (-not $child.HasExited) { $child.Kill($true); $child.WaitForExit(5000) | Out-Null }
        $child.Dispose()
    }
    if (Test-Path (Join-Path $root 'logs/error.log')) { Get-Content (Join-Path $root 'logs/error.log') | Write-Host }
    Write-Host "Disposable check files: $root"
}
