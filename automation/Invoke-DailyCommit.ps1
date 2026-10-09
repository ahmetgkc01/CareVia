param(
    [string]$RepositoryPath = "C:\Users\demo\Documents\GitHub\Carevia"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$expectedPath = "C:\Users\demo\Documents\GitHub\Carevia"
$resolvedPath = (Resolve-Path -LiteralPath $RepositoryPath).Path
if ($resolvedPath -ne $expectedPath) {
    throw "Unexpected repository path: $resolvedPath"
}

$logDirectory = Join-Path $resolvedPath "automation\logs"
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$logPath = Join-Path $logDirectory ("daily-commit-{0}.log" -f (Get-Date -Format "yyyy-MM-dd-HHmmss"))
Start-Transcript -LiteralPath $logPath -Force | Out-Null

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $gitArguments = @("-c", "safe.directory=$resolvedPath") + $Arguments
    Invoke-CheckedCommand -Command "git" -Arguments $gitArguments
}

try {
    Set-Location -LiteralPath $resolvedPath

    $branch = (& git -c "safe.directory=$resolvedPath" branch --show-current).Trim()
    if ($branch -ne "main") {
        throw "Daily commit only runs on main; current branch is '$branch'."
    }

    $status = & git -c "safe.directory=$resolvedPath" status --porcelain=v1
    if (-not $status) {
        Write-Output "No changes detected; nothing to commit."
        exit 0
    }

    $conflicts = & git -c "safe.directory=$resolvedPath" diff --name-only --diff-filter=U
    if ($conflicts) {
        throw "Merge conflicts detected; automatic commit stopped."
    }

    $blockedPattern = '(^|/)(\.env($|\.)|.*\.(pem|key|p12|pfx|sqlite3?|dump|log)$|node_modules/|dist/|test-results/|playwright-report/)'
    $allowedExamples = @(".env.example", "deploy/.env.production.example")
    foreach ($line in $status) {
        $path = $line.Substring(3).Replace("\", "/")
        if ($path.Contains(" -> ")) {
            $path = $path.Split(" -> ")[-1]
        }
        if ($path -match $blockedPattern -and $allowedExamples -notcontains $path) {
            throw "Blocked sensitive or generated path: $path"
        }
    }

    Invoke-Git -Arguments @("fetch", "origin", "main")
    $localHead = (& git -c "safe.directory=$resolvedPath" rev-parse HEAD).Trim()
    $remoteHead = (& git -c "safe.directory=$resolvedPath" rev-parse origin/main).Trim()
    if ($localHead -ne $remoteHead) {
        throw "Local main and origin/main differ; resolve this before automatic commit."
    }

    $promptPath = Join-Path $resolvedPath "automation\daily-commit-prompt.md"
    $messagePath = Join-Path ([System.IO.Path]::GetTempPath()) "carevia-daily-commit-message.txt"
    if (Test-Path -LiteralPath $messagePath) {
        Remove-Item -LiteralPath $messagePath -Force
    }
    $prompt = Get-Content -LiteralPath $promptPath -Raw -Encoding utf8
    $codexCommand = Get-Command codex.exe -ErrorAction SilentlyContinue
    if ($codexCommand) {
        $codexPath = $codexCommand.Source
    }
    else {
        $codexPath = Get-ChildItem -Path "$env:USERPROFILE\.vscode\extensions\openai.chatgpt-*\bin\windows-x86_64\codex.exe" -File |
            Sort-Object FullName -Descending |
            Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $codexPath -or -not (Test-Path -LiteralPath $codexPath)) {
        throw "Codex CLI could not be found."
    }
    Invoke-CheckedCommand $codexPath exec --ephemeral --approve-for-me --cd $resolvedPath --output-last-message $messagePath $prompt

    $commitMessage = (Get-Content -LiteralPath $messagePath -Raw -Encoding utf8).Trim()
    Remove-Item -LiteralPath $messagePath -Force
    if ($commitMessage -notmatch '^(feat|fix|docs|refactor|test|chore|build|ci|perf|style)(\([^)]+\))?: .{1,65}$' -or $commitMessage.Contains("`n")) {
        throw "Codex returned an invalid commit title: $commitMessage"
    }

    Push-Location (Join-Path $resolvedPath "backend")
    try {
        Invoke-CheckedCommand "..\.venv\Scripts\python.exe" -m ruff check .
        Invoke-CheckedCommand "..\.venv\Scripts\python.exe" -m pytest
        Invoke-CheckedCommand "..\.venv\Scripts\python.exe" manage.py makemigrations --check --dry-run --settings=config.settings.testing
    }
    finally {
        Pop-Location
    }

    Push-Location (Join-Path $resolvedPath "frontend")
    try {
        Invoke-CheckedCommand npm.cmd run lint
        Invoke-CheckedCommand npm.cmd run test:run
        Invoke-CheckedCommand npm.cmd run build
    }
    finally {
        Pop-Location
    }

    Invoke-Git -Arguments @("diff", "--check")
    Invoke-Git -Arguments @("add", "-A")
    $stagedFiles = & git -c "safe.directory=$resolvedPath" diff --cached --name-only
    if (-not $stagedFiles) {
        Write-Output "No staged changes remain; nothing to commit."
        exit 0
    }
    foreach ($path in $stagedFiles) {
        $normalizedPath = $path.Replace("\", "/")
        if ($normalizedPath -match $blockedPattern -and $allowedExamples -notcontains $normalizedPath) {
            Invoke-Git -Arguments @("reset")
            throw "Blocked path reached staging; staging was cleared: $normalizedPath"
        }
    }

    Invoke-Git -Arguments @("commit", "-m", $commitMessage)
    Invoke-Git -Arguments @("push", "origin", "main")
    Write-Output "Daily commit completed and pushed: $commitMessage"
}
catch {
    Write-Error $_
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
