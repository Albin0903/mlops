param(
    [string]$Path = $PWD.Path
)

$venvActivate = Join-Path $Path '.venv\Scripts\Activate.ps1'

if (-not (Test-Path $venvActivate)) {
    Write-Error "Aucun venv trouve dans: $Path (.venv\Scripts\Activate.ps1 introuvable)"
    exit 1
}

. $venvActivate
Write-Host "venv active: $venvActivate" -ForegroundColor Green
