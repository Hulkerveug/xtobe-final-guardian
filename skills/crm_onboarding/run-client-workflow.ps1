param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$LeadFile,

    [ValidatePattern('^[A-Za-z0-9_-]{1,64}$')]
    [string]$TemplateId = 'welcome_v1'
)

$ErrorActionPreference = 'Stop'
$SkillRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $SkillRoot)
$LogDir = Join-Path $ProjectRoot 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Values cross the PowerShell/Python boundary as JSON, never interpolated Python source.
$Request = @{
    lead_file_path = (Resolve-Path -LiteralPath $LeadFile).Path
    template_id = $TemplateId
} | ConvertTo-Json -Compress

$Python = $null
foreach ($Candidate in @('py', 'python')) {
    $Command = Get-Command $Candidate -ErrorAction SilentlyContinue
    if (-not $Command) { continue }
    & $Command.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $Python = $Command; break }
}
if (-not $Python) { throw 'Python 3.11 or newer is required.' }

Write-Host '[GATE] Running local CRM workflow; no network tools are invoked.' -ForegroundColor Green
$Result = $Request | & $Python.Source (Join-Path $SkillRoot 'crm_workflow.py')
if ($LASTEXITCODE -ne 0) { throw "CRM workflow failed with exit code $LASTEXITCODE" }

$OutputPath = Join-Path $LogDir 'last_run.json'
$TempOutput = Join-Path $LogDir ".last_run.$PID.tmp"
[IO.File]::WriteAllText($TempOutput, ($Result -join [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $TempOutput -Destination $OutputPath -Force
Write-Host "[DISPATCH] Results persisted atomically at $OutputPath" -ForegroundColor Cyan
