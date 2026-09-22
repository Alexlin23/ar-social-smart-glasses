param([string]$PythonPath = '')
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
if (-not $PythonPath) {
    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled) { $PythonPath = $bundled }
    else {
        $command = Get-Command python -ErrorAction SilentlyContinue
        if ($command) { $PythonPath = $command.Source }
    }
}
if (-not $PythonPath) { throw 'Python 3.10+ required. Use -PythonPath C:\path\to\python.exe' }
& $PythonPath -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
if ($LASTEXITCODE -ne 0) { throw 'Python is unavailable or too old.' }
$runtime = Join-Path $projectRoot '.venv-ar\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtime)) {
    & $PythonPath -m venv (Join-Path $projectRoot '.venv-ar')
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& $runtime -m pip install -r (Join-Path $projectRoot 'requirements-ar.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $runtime (Join-Path $projectRoot 'ar_setup_models.py')
if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }
& $runtime (Join-Path $projectRoot 'run_ar_view.py') --check
if ($LASTEXITCODE -ne 0) { throw 'AR environment check failed.' }
Write-Output 'Ready. Run launch_ar.cmd --demo for the UI demo, or launch_ar.cmd for the camera.'
