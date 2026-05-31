<#
.SYNOPSIS
    Syncs the Moira project memory between the current working directory and the central OneDrive location.

.DESCRIPTION
    This script helps maintain the robust memory system.
    Run it when starting a new worktree or when you want to pull the latest central memory.
#>

$centralMemory = "\\?\C:\Users\nilad\OneDrive\.moira-memory\moira"
$localRemember = ".remember\remember.md"
$centralRemember = Join-Path $centralMemory "remember.md"

Write-Host "Moira Memory Sync Tool"
Write-Host "======================"
Write-Host "Central: $centralMemory"
Write-Host "Local:   $localRemember"
Write-Host ""

if (-not (Test-Path $centralMemory)) {
    Write-Error "Central memory directory not found at $centralMemory"
    exit 1
}

$choice = Read-Host "Do you want to (P)ull from central or (P)ush local to central? [P/u]"

if ($choice -eq 'u' -or $choice -eq 'U') {
    # Push local to central
    if (Test-Path $localRemember) {
        Copy-Item $localRemember $centralRemember -Force
        Write-Host "Pushed local memory to central location."
    } else {
        Write-Warning "No local .remember/remember.md found to push."
    }
} else {
    # Pull central to local
    if (Test-Path $centralRemember) {
        Copy-Item $centralRemember $localRemember -Force
        Write-Host "Pulled central memory into local .remember/remember.md"
    } else {
        Write-Warning "No central remember.md found."
    }
}

Write-Host "Done."
