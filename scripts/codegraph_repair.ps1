# CodeGraph MCP 복구 스크립트 (Windows)
# - 손상된 daemon.pid(디렉터리/잔여 파일) 정리
# - 잠금 해제 및 인덱스 동기화
# - MCP 연결 상태 점검

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$CodeGraphDir = Join-Path $ProjectRoot ".codegraph"

function Remove-StaleDaemonArtifacts {
    param([string]$Dir)

    if (-not (Test-Path $Dir)) {
        return
    }

    $targets = @(
        "daemon.pid",
        "daemon.sock",
        "daemon.log"
    )

    foreach ($name in $targets) {
        $path = Join-Path $Dir $name
        if (-not (Test-Path $path)) {
            continue
        }

        $item = Get-Item -LiteralPath $path -Force
        if ($item.PSIsContainer) {
            Write-Host "[repair] Removing corrupt directory: $path"
            Remove-Item -LiteralPath $path -Recurse -Force
            continue
        }

        if ($name -eq "daemon.log") {
            Write-Host "[repair] Clearing stale daemon log: $path"
            Set-Content -LiteralPath $path -Value "" -Encoding utf8
            continue
        }

        Write-Host "[repair] Removing stale file: $path"
        Remove-Item -LiteralPath $path -Force
    }

    Get-ChildItem -LiteralPath $Dir -Force -Filter "daemon.pid.*.tmp" -ErrorAction SilentlyContinue |
        ForEach-Object {
            Write-Host "[repair] Removing temp lock file: $($_.FullName)"
            Remove-Item -LiteralPath $_.FullName -Force
        }
}

Push-Location $ProjectRoot
try {
    if (-not (Get-Command codegraph -ErrorAction SilentlyContinue)) {
        throw "codegraph CLI not found in PATH. Run: npm install -g codegraph (or use the official installer)."
    }

    Write-Host "[repair] CodeGraph version: $(codegraph version)"
    Remove-StaleDaemonArtifacts -Dir $CodeGraphDir

    Write-Host "[repair] Unlocking stale index lock (if any)..."
    codegraph unlock | Out-Host

    Write-Host "[repair] Syncing index..."
    codegraph sync | Out-Host

    Write-Host "[repair] Status:"
    codegraph status | Out-Host

    if (Get-Command grok -ErrorAction SilentlyContinue) {
        Write-Host "[repair] MCP doctor:"
        grok mcp doctor codegraph | Out-Host
    } else {
        Write-Host "[repair] grok CLI not found; skipped MCP doctor."
    }

    Write-Host "[repair] Done."
}
finally {
    Pop-Location
}