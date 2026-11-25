# Clipstorm setup for Windows. Run setup.bat (double-click) - it calls this file.
# Installs what is missing (Python, ffmpeg), makes a private Python environment in .venv, installs the
# libraries, and makes a .env from the example. Safe to run again: it only adds what is not there.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Say($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Yellow }
function Have($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }
# Named Get-Missing, not Winget: a function called Winget is what "winget install" ran, so it called itself forever.
function Get-Missing($id, $what) {
    if (-not (Have "winget.exe")) { throw "$what is missing and winget is not available. Install $what by hand, then run setup again." }
    Say "Installing $what (this can take a few minutes)"
    winget.exe install --id $id -e --accept-source-agreements --accept-package-agreements --silent
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

Say "Checking this PC"
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$free = [math]::Round((Get-PSDrive -Name (Get-Location).Drive.Name).Free / 1GB)
Write-Host "Memory: $ram GB   Free disk here: $free GB   Folder: $PSScriptRoot"
if ($ram -lt 8) { Write-Host "Less than 8 GB of memory: it will work, but rendering will be slow." -ForegroundColor Red }
if ($free -lt 15) { Write-Host "Less than 15 GB free: a long live recording needs room for its stream pieces." -ForegroundColor Red }
if ($PSScriptRoot.Length -gt 100) { Write-Host "This folder path is long. Windows cannot open paths over 260 characters; C:\clipstorm is safer." -ForegroundColor Red }

# ---- Python 3.10 to 3.13 (the speech library has no build for newer ones yet)
# The checks go through cmd so a missing version is just a "no": in Windows PowerShell, a message a program writes
# to its error stream stops the whole script while errors are set to stop ("py.exe : No suitable Python runtime
# found" ended setup on a PC that has 3.11, 3.13 and 3.15, because 3.12 was asked for first). A version that is
# listed but broken (its files deleted) also answers "no", and the plain `python` is tried after.
$py = $null
foreach ($v in "3.12", "3.13", "3.11", "3.10") {
    if (Have "py") { cmd /c "py -$v -c ""print(1)"" >nul 2>nul"; if ($LASTEXITCODE -eq 0) { $py = @("py", "-$v"); break } }
}
if (-not $py -and (Have "python")) {
    $ok = cmd /c "python -c ""import sys; print(int((3,10) <= sys.version_info[:2]))"" 2>nul"
    if ($ok -eq "1") { $py = @("python") }
}
if (-not $py) { Get-Missing "Python.Python.3.12" "Python 3.12"; $py = @("py", "-3.12") }
Write-Host ("Python: " + (& $py[0] $py[1..9] --version))

# ---- ffmpeg (cuts, renders and records)
if (-not (Have "ffmpeg")) { Get-Missing "Gyan.FFmpeg" "ffmpeg" }
if (-not (Have "ffmpeg")) { throw "ffmpeg was installed but this window cannot see it yet. Close this window and run setup.bat once more." }
Write-Host ("ffmpeg: " + ((& ffmpeg -version | Select-Object -First 1)))

# ---- the libraries, in a folder of their own so nothing else on the PC is touched
Say "Making the Python environment (.venv)"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $py[0] $py[1..9] -m venv .venv }
$vpy = ".venv\Scripts\python.exe"
& $vpy -m pip install --upgrade pip --quiet
Say "Installing the libraries"
& $vpy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    # One library that will not install (usually the on-this-PC speech engine on a very new Python) must not
    # stop everything: the rest are installed one by one, and what is missing is named.
    Write-Host "Not everything installed in one go. Installing one at a time." -ForegroundColor Red
    $missing = @()
    foreach ($line in Get-Content requirements.txt) {
        $l = $line.Trim(); if (-not $l -or $l.StartsWith("#")) { continue }
        & $vpy -m pip install $l --quiet
        if ($LASTEXITCODE -ne 0) { $missing += $l }
    }
    if ($missing) {
        Write-Host ("Could not install: " + ($missing -join ", ")) -ForegroundColor Red
        Write-Host "Clipstorm still runs. Without sherpa-onnx, choose a speech service under Settings > Transcription instead of 'on this PC'."
    }
}
& $vpy -m pip install --upgrade yt-dlp --quiet     # sites change often; the newest downloader works best

if (-not (Test-Path ".env") -and (Test-Path ".env.example")) { Copy-Item ".env.example" ".env"; Write-Host "Made .env from .env.example (your keys go in the app's Settings pages, not here)." }

Say "Checking it starts"
& $vpy -c "import studio.server; print('Clipstorm is ready.')"
if ($LASTEXITCODE -ne 0) { throw "The app did not load. Copy the lines above and send them to whoever set this up." }
Write-Host ""
Write-Host "Done. Double-click start.bat to open Clipstorm." -ForegroundColor Green
