$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv" -PathType Container)) {
    & ".\scripts\setup-venv.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment setup failed; the app was not started."
    }
}

if (-not (Test-Path ".venv\setup.complete" -PathType Leaf)) {
    throw "Virtual environment setup is incomplete. Run .\scripts\setup-venv.ps1 before starting the app."
}

$chainlit = Start-Process -FilePath ".venv\Scripts\chainlit.exe" -ArgumentList @("run", "src/kathrena/chat_interface/app.py") -NoNewWindow -PassThru
$ragIndex = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList @("-m", "kathrena.rag_index") -NoNewWindow -PassThru

Write-Host "Chat app (PID $($chainlit.Id)) and RAG indexer (PID $($ragIndex.Id)) running - Ctrl+C to stop both."
try {
    Wait-Process -Id $chainlit.Id, $ragIndex.Id
} finally {
    foreach ($proc in @($chainlit, $ragIndex)) {
        if (-not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
