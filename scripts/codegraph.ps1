# Windows 에이전트/셸 호환용 CodeGraph 래퍼
# Cursor/Grok 셸이 `(cd path ; codegraph ...)` 형태를 PowerShell에서 파싱하지 못하는 경우,
# 아래처럼 호출하세요:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/codegraph.ps1 explore WorkerThread

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Get-Command codegraph -ErrorAction SilentlyContinue)) {
    throw "codegraph CLI not found in PATH."
}

if ($args.Count -eq 0) {
    codegraph --help
    exit $LASTEXITCODE
}

& codegraph @args
exit $LASTEXITCODE