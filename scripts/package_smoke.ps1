$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SpecPath = Join-Path $RepoRoot "pdf_master.spec"
$SmokeRoot = Join-Path $RepoRoot "build\package_smoke"
$SmokeDist = Join-Path $SmokeRoot "dist"
$SmokeWork = Join-Path $SmokeRoot "work"
$ExePath = Join-Path $SmokeDist "PDF_Master_v4.5.5.exe"

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

    if (-not (Test-Path -LiteralPath $ExePath)) {
        throw "Packaged executable was not found: $ExePath"
    }

    $process = Start-Process -FilePath $ExePath -ArgumentList "--smoke" -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "Packaged smoke failed with exit code $($process.ExitCode)"
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    Pop-Location
}
