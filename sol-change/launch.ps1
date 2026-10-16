param([int]$Port = 8770, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = $null
$taskCandidates = @()
if ($env:SOL_CHANGE_PYTHON) { $taskCandidates += $env:SOL_CHANGE_PYTHON }
$taskPythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($taskPythonCommand) { $taskCandidates += $taskPythonCommand.Source }
$taskCandidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
foreach ($taskCandidate in $taskCandidates) {
    if (Test-Path -LiteralPath $taskCandidate) {
        try {
            & $taskCandidate -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { $taskPython = $taskCandidate; break }
        } catch { }
    }
}
if (-not $taskPython) { throw 'Python 3.11+ is required. Install Python or set SOL_CHANGE_PYTHON to its executable path.' }
$taskArgs = @((Join-Path $taskRoot 'app.py'), '--port', "$Port")
if (-not $NoBrowser) { $taskArgs += '--open' }
& $taskPython @taskArgs
exit $LASTEXITCODE
