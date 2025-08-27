<# PowerShell: Apply patch and tag v1.01
Usage:
  .\tag_release_1_01.ps1 -Branch main -PatchFile .\release_1_01.patch
#>
param(
  [string]$Branch = "main",
  [string]$PatchFile = ".\release_1_01.patch"
)

$ErrorActionPreference = "Stop"

Write-Host ">> Checking repo state..."
git rev-parse --is-inside-work-tree | Out-Null

Write-Host ">> Switching to branch: $Branch"
git checkout -B $Branch

Write-Host ">> Dry-run applying patch..."
git apply --check $PatchFile

Write-Host ">> Applying patch..."
git apply --whitespace=fix $PatchFile

Write-Host ">> Committing changes..."
git add -A
try {
  git commit -m "Release 1.01: universal trade-mode (simulated/real devnet/mainnet)"
} catch {
  Write-Host "No changes to commit (skip)"
}

Write-Host ">> Tagging v1.01..."
git tag -a v1.01 -m "Release 1.01 — universal trade-mode switch"

Write-Host ">> Pushing branch + tags..."
git push origin $Branch --tags

Write-Host "✅ Done."
