$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DefaultDest = Join-Path $HOME ".config/opencode/skills"
$Dest = if ($args.Count -gt 0) { $args[0] } else { $DefaultDest }
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$Stage = Join-Path ([System.IO.Path]::GetTempPath()) ("shortform-skills-" + [guid]::NewGuid().ToString("N"))
$Backup = Join-Path (Join-Path $Dest ".shortform-backups") $Stamp

try {
    New-Item -ItemType Directory -Force -Path $Stage, $Dest | Out-Null

    # Stage every skill before changing the current installation.
    Get-ChildItem -Path $Root -Directory | ForEach-Object {
        $SkillFile = Join-Path $_.FullName "SKILL.md"
        if (Test-Path $SkillFile) {
            Copy-Item -Recurse $_.FullName (Join-Path $Stage $_.Name)
        }
    }

    $Scoring = Join-Path $Root "references/viral-scoring.md"
    if (Test-Path $Scoring) {
        foreach ($Skill in @("shortform-video-editor", "viral-moment-detection")) {
            $RefDir = Join-Path (Join-Path $Stage $Skill) "references"
            New-Item -ItemType Directory -Force -Path $RefDir | Out-Null
            Copy-Item $Scoring (Join-Path $RefDir "viral-scoring.md")
        }
    }

    $Fps = Join-Path $Root "references/export-and-fps.md"
    if (Test-Path $Fps) {
        foreach ($Skill in @("shortform-video-editor", "ffmpeg-rendering")) {
            $RefDir = Join-Path (Join-Path $Stage $Skill) "references"
            New-Item -ItemType Directory -Force -Path $RefDir | Out-Null
            Copy-Item $Fps (Join-Path $RefDir "export-and-fps.md")
        }
    }

    $Schema = Join-Path $Root "schemas/edit-decision-list.schema.json"
    if (Test-Path $Schema) {
        $SchemaDir = Join-Path (Join-Path $Stage "edit-decision-list") "schemas"
        New-Item -ItemType Directory -Force -Path $SchemaDir | Out-Null
        Copy-Item $Schema (Join-Path $SchemaDir "edit-decision-list.schema.json")
    }

    $Defaults = Join-Path $Root "config/project-defaults.json"
    if (Test-Path $Defaults) {
        $ConfigDir = Join-Path (Join-Path $Stage "shortform-video-editor") "config"
        New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
        Copy-Item $Defaults (Join-Path $ConfigDir "project-defaults.json")
    }

    Get-ChildItem -Path $Stage -Directory | ForEach-Object {
        $Target = Join-Path $Dest $_.Name
        if (Test-Path $Target) {
            $BackupSkill = Join-Path $Backup $_.Name
            New-Item -ItemType Directory -Force -Path $Backup | Out-Null
            Move-Item -Force $Target $BackupSkill
        }
        Move-Item -Force $_.FullName $Target
        Write-Host "Installed $($_.Name)"
    }

    Write-Host "OpenCode skills installed to: $Dest"
    if (Test-Path $Backup) { Write-Host "Previous versions backed up to: $Backup" }
    Write-Host "Reload OpenCode if the skills are not discovered."
}
finally {
    if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
}
