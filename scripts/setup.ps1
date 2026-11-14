param(
    [string]$Destination = (Join-Path $HOME ".config/opencode/skills")
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$Launcher = Get-Command py -ErrorAction SilentlyContinue
if ($Launcher) {
    $PythonCommand = "py"
    $PythonPrefix = @("-3")
} else {
    $PythonCommand = "python"
    $PythonPrefix = @()
}

Write-Host "Installing the shortform-editor CLI and audio/visual/download extras..."
& $PythonCommand @PythonPrefix -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip." }

& $PythonCommand @PythonPrefix -m pip install -e "$Root[audio,visual,download]"
if ($LASTEXITCODE -ne 0) { throw "Could not install the shortform-editor package and optional extras." }

Write-Host "Installing OpenCode skills..."
& (Join-Path $PSScriptRoot "install.ps1") $Destination
if ($LASTEXITCODE -ne 0) { throw "Could not install OpenCode skills." }

$Ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
$Ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
if (-not $Ffmpeg -or -not $Ffprobe) {
    Write-Warning "The CLI and skills are installed, but FFmpeg and ffprobe are required before rendering."
    Write-Warning "Install an FFmpeg build that includes ffprobe, libx264 (or NVENC), and the subtitles filter, then add its bin folder to PATH."
    exit 1
}

Write-Host "Running the environment doctor..."
& $PythonCommand @PythonPrefix -m shortform_editor.cli doctor
if ($LASTEXITCODE -ne 0) {
    throw "The environment doctor found missing required executables, encoders, filters or Python modules. Review its report before rendering."
}

Write-Host "Setup complete. Reload OpenCode if it does not discover the installed skills."
