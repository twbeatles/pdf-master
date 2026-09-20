$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SpecPath = Join-Path $RepoRoot "pdf_master.spec"
$SmokeRoot = Join-Path $RepoRoot "build\package_smoke"
$SmokeDist = Join-Path $SmokeRoot "dist"
$SmokeWork = Join-Path $SmokeRoot "work"

Push-Location $RepoRoot
try {
    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = ""

    if (Test-Path -LiteralPath $SmokeRoot) {
        Remove-Item -LiteralPath $SmokeRoot -Recurse -Force
    }

    python -m PyInstaller $SpecPath --clean --noconfirm --distpath $SmokeDist --workpath $SmokeWork
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    # EXE 이름은 APP_VERSION을 따라가므로 하드코딩하지 않고 산출물에서 찾는다.
    # (SmokeRoot는 매 실행마다 정리되므로 보통 1개만 존재)
    $builtExe = Get-ChildItem -LiteralPath $SmokeDist -Filter "PDF_Master_v*.exe" -File |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if (-not $builtExe) {
        throw "Packaged executable was not found in: $SmokeDist"
    }
    $ExePath = $builtExe.FullName

    $process = Start-Process -FilePath $ExePath -ArgumentList "--smoke" -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "Packaged smoke failed with exit code $($process.ExitCode)"
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    Pop-Location
}
