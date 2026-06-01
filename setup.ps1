# setup.ps1 - NEXUS one-time setup

$ErrorActionPreference = "Stop"

Write-Host "`n=== NEXUS Setup ===" -ForegroundColor Cyan

# --- Check prerequisites ---
Write-Host "`n[1/6] Checking prerequisites..." -ForegroundColor Yellow

foreach ($cmd in @("uv", "node", "git")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "$cmd not found. Please install it first."
        exit 1
    }
    Write-Host "  $cmd" -ForegroundColor Green
}

if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
    Write-Warning "  ! ollama not found - install from https://ollama.com to enable local AI"
} else {
    Write-Host "  ollama" -ForegroundColor Green
}

# --- Install Python deps ---
Write-Host "`n[2/6] Installing Python dependencies..." -ForegroundColor Yellow
uv sync
Write-Host "  Python deps installed" -ForegroundColor Green

# --- Build frontend ---
Write-Host "`n[3/6] Building frontend..." -ForegroundColor Yellow
Push-Location frontend
npm install
npm run build
Pop-Location
Write-Host "  Frontend built -> frontend/dist/" -ForegroundColor Green

# --- Create data dir ---
Write-Host "`n[4/6] Creating ~/.nexus/ data directory..." -ForegroundColor Yellow
$nexusDir = Join-Path $env:USERPROFILE ".nexus"
New-Item -ItemType Directory -Force -Path $nexusDir | Out-Null
Write-Host "  $nexusDir" -ForegroundColor Green

# --- Copy config ---
Write-Host "`n[5/6] Setting up config..." -ForegroundColor Yellow
$configDest = "nexus.toml"
if (-not (Test-Path $configDest)) {
    Copy-Item "nexus.toml.example" $configDest
    Write-Host "  nexus.toml created from example" -ForegroundColor Green
    Write-Host "  ! Edit nexus.toml to set your Notion token and other credentials" -ForegroundColor Yellow
} else {
    Write-Host "  nexus.toml already exists - skipped" -ForegroundColor Green
}

# --- Pull Ollama models ---
Write-Host "`n[6/6] Pulling Ollama models (this may take a while)..." -ForegroundColor Yellow
if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    foreach ($model in @("qwen2.5:7b", "nomic-embed-text")) {
        Write-Host "  Pulling $model..."
        ollama pull $model
        Write-Host "  $model" -ForegroundColor Green
    }
} else {
    Write-Host "  ! Skipped (ollama not installed)" -ForegroundColor Yellow
}

# --- Register Task Scheduler ---
Write-Host "`nRegistering Windows Task Scheduler digest task..." -ForegroundColor Yellow
$taskName = "NEXUS-DailyDigest"
$uvPath = (Get-Command uv).Source
$projectDir = (Get-Location).Path
$action = New-ScheduledTaskAction -Execute $uvPath -Argument "run nexus digest" -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00AM"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -StartWhenAvailable

try {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "NEXUS daily morning digest" | Out-Null
    Write-Host "  Task registered (runs daily at 08:00)" -ForegroundColor Green
} catch {
    Write-Warning "  ! Could not register Task Scheduler task: $_"
    Write-Warning "  ! Run setup.ps1 as Administrator to register it"
}

Write-Host "`n=== Setup complete! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Edit nexus.toml with your credentials" -ForegroundColor Gray
Write-Host "  2. Run: uv run nexus connect (to authorize Google/Notion)" -ForegroundColor Gray
Write-Host "  3. Run: uv run nexus serve (to start the web UI)" -ForegroundColor Gray
Write-Host "  4. Or:  uv run nexus ask what is on my calendar today" -ForegroundColor Gray
Write-Host ""
