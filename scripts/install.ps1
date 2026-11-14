$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DefaultDest = Join-Path $HOME ".config/opencode/skills"
$Dest = if ($args.Count -gt 0) { $args[0] } else { $DefaultDest }

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Get-ChildItem -Path $Root -Directory | ForEach-Object {
    $SkillFile = Join-Path $_.FullName "SKILL.md"
    if (Test-Path $SkillFile) {
        $Target = Join-Path $Dest $_.Name
        if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
        Copy-Item -Recurse $_.FullName $Target
        Write-Host "Installed $($_.Name)"
    }
}
$RuntimeSource = Join-Path $Root "shortform_editor"
$SkillRuntime = Join-Path $Dest "shortform-video-editor/runtime"
if (Test-Path $RuntimeSource) {
    New-Item -ItemType Directory -Force -Path $SkillRuntime | Out-Null
    Copy-Item -Path (Join-Path $RuntimeSource "*") -Destination $SkillRuntime -Recurse -Force
    Write-Host "Installed shortform editor runtime"
}
foreach ($SharedDir in @("references", "schemas", "config", "docs")) {
    $SharedSource = Join-Path $Root $SharedDir
    $SharedTarget = Join-Path $Dest $SharedDir
    if (Test-Path $SharedSource) {
        if (Test-Path $SharedTarget) { Remove-Item -Recurse -Force $SharedTarget }
        Copy-Item -Recurse $SharedSource $SharedTarget
        Write-Host "Installed shared $SharedDir"
    }
}
Write-Host "OpenCode skills installed to: $Dest"
Write-Host "Restart/reload OpenCode if the new skills are not discovered."
