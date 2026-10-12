<#
.SYNOPSIS
    Creates .venv and installs the project, with the CUDA torch build if an NVIDIA GPU is present.

    Two ordered pip installs, wrapped so it's one command instead of a manual dance every time
    (see src/kathrena/voice_log/README.md and src/kathrena/rag_index/README.md for why the order
    matters: pyproject.toml alone can't pin torch to the CUDA index - see Decisions Log Round 15).

.PARAMETER CudaIndex
    The PyTorch wheel index to use, e.g. cu130 for CUDA 13.0. Pass "cpu" to skip the CUDA install
    and let pip pull the default CPU-only torch build instead.
#>
param(
    [string]$CudaIndex = "cu130"
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$setupMarker = ".venv\setup.complete"
if (Test-Path $setupMarker) {
    Remove-Item $setupMarker
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed."
    }
}

.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed."
}

if ($CudaIndex -ne "cpu") {
    .venv\Scripts\python.exe -m pip install torch torchvision `
        --index-url "https://download.pytorch.org/whl/$CudaIndex"
    if ($LASTEXITCODE -ne 0) {
        throw "CUDA PyTorch installation failed."
    }
}

.venv\Scripts\python.exe -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "Project dependency installation failed."
}

New-Item -ItemType File -Path $setupMarker -Force | Out-Null
