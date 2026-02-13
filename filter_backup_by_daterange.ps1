# Filter LocoKit1 Backup by Date Range (Windows PowerShell Wrapper)
#
# This script provides an interactive interface to filter LocoKit1 backups by date range.
#
# Usage:
#   .\filter_backup_by_daterange.ps1
#   # Or with parameters:
#   .\filter_backup_by_daterange.ps1 -BackupDir "c:\backup" -StartDate "2024-12-15 00:00:00" -EndDate "2024-12-31 23:59:59"

param(
    [string]$BackupDir,
    [string]$StartDate,
    [string]$EndDate,
    [string]$OutputDir,
    [int]$Days
)

# Define color output
$ColorInfo = 'Cyan'
$ColorSuccess = 'Green'
$ColorWarning = 'Yellow'
$ColorError = 'Red'

function Write-Title {
    param([string]$Title)
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor $ColorInfo
    Write-Host $Title -ForegroundColor $ColorInfo
    Write-Host "=" * 80 -ForegroundColor $ColorInfo
}

function Write-Status {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor $ColorSuccess
}

function Write-Problem {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor $ColorWarning
}

function Write-Error2 {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor $ColorError
}

function Validate-Directory {
    param(
        [string]$Path,
        [string]$Description
    )
    
    if (-not $Path) {
        Write-Error2 "$Description is required"
        return $false
    }
    
    if (-not (Test-Path $Path)) {
        Write-Error2 "$Description does not exist: $Path"
        return $false
    }
    
    if (-not (Test-Path "$Path\TimelineItem" -PathType Container)) {
        Write-Error2 "TimelineItem directory not found. Is this a valid LocoKit1 backup?"
        return $false
    }
    
    return $true
}

function Parse-DateTime {
    param([string]$DateString)
    
    try {
        return [DateTime]::ParseExact($DateString, "yyyy-MM-dd HH:mm:ss", [System.Globalization.CultureInfo]::InvariantCulture)
    }
    catch {
        return $null
    }
}

function Prompt-ForBackupDir {
    Write-Host ""
    Write-Host "Enter the path to your LocoKit1 backup directory" -ForegroundColor $ColorInfo
    Write-Host "Example: c:\tmp\iCloud\iCloudDrive\iCloud~com~bigpaua~LearnerCoacher\Backups" -ForegroundColor Gray
    Write-Host ""
    
    $Path = Read-Host "Backup directory"
    
    if (-not (Validate-Directory $Path "Backup directory")) {
        Write-Error2 "Invalid backup directory"
        exit 1
    }
    
    return $Path
}

function Prompt-ForDateRange {
    Write-Host ""
    Write-Host "Select how you want to specify the date range:" -ForegroundColor $ColorInfo
    Write-Host "1. Specific date range (e.g., Dec 15-31, 2024)"
    Write-Host "2. Single date (full day, e.g., Dec 25, 2024)"
    Write-Host "3. Last N days (e.g., last 7 days)"
    Write-Host ""
    
    $choice = Read-Host "Enter choice (1-3)"
    
    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "Enter start date and time" -ForegroundColor $ColorInfo
            Write-Host "Format: YYYY-MM-DD HH:MM:SS (e.g., 2024-12-15 00:00:00)" -ForegroundColor Gray
            $start = Read-Host "Start date/time"
            
            $startDt = Parse-DateTime $start
            if (-not $startDt) {
                Write-Error2 "Invalid date format"
                return $null
            }
            
            Write-Host ""
            Write-Host "Enter end date and time" -ForegroundColor $ColorInfo
            Write-Host "Format: YYYY-MM-DD HH:MM:SS (e.g., 2024-12-31 23:59:59)" -ForegroundColor Gray
            $end = Read-Host "End date/time"
            
            $endDt = Parse-DateTime $end
            if (-not $endDt) {
                Write-Error2 "Invalid date format"
                return $null
            }
            
            if ($startDt -gt $endDt) {
                Write-Error2 "Start date cannot be after end date"
                return $null
            }
            
            return @{
                Type = "range"
                Start = $start
                End = $end
            }
        }
        "2" {
            Write-Host ""
            Write-Host "Enter the date to filter" -ForegroundColor $ColorInfo
            Write-Host "Format: YYYY-MM-DD (e.g., 2024-12-25)" -ForegroundColor Gray
            $date = Read-Host "Date"
            
            # Validate date format
            try {
                [DateTime]::ParseExact($date, "yyyy-MM-dd", [System.Globalization.CultureInfo]::InvariantCulture) | Out-Null
            }
            catch {
                Write-Error2 "Invalid date format"
                return $null
            }
            
            return @{
                Type = "single"
                Date = $date
            }
        }
        "3" {
            Write-Host ""
            Write-Host "Enter number of days to include" -ForegroundColor $ColorInfo
            Write-Host "Example: 7 for last week" -ForegroundColor Gray
            $days = Read-Host "Days"
            
            if (-not [int]::TryParse($days, [ref]$days) -or $days -le 0) {
                Write-Error2 "Invalid number of days"
                return $null
            }
            
            return @{
                Type = "days"
                Days = $days
            }
        }
        default {
            Write-Error2 "Invalid choice"
            return $null
        }
    }
}

function Prompt-ForOutputDir {
    Write-Host ""
    Write-Host "Enter output directory for filtered backup" -ForegroundColor $ColorInfo
    Write-Host "Leave blank to use './filtered_backup'" -ForegroundColor Gray
    
    $dir = Read-Host "Output directory"
    
    if (-not $dir) {
        $dir = "./filtered_backup"
    }
    
    return $dir
}

function Format-FileSize {
    param([long]$Size)
    
    if ($Size -ge 1GB) { return "{0:N2} GB" -f ($Size / 1GB) }
    if ($Size -ge 1MB) { return "{0:N2} MB" -f ($Size / 1MB) }
    if ($Size -ge 1KB) { return "{0:N2} KB" -f ($Size / 1KB) }
    return "$Size Bytes"
}

function Show-SummaryInfo {
    param(
        [string]$BackupDir,
        [string]$DateRange
    )
    
    Write-Host ""
    Write-Host "Backup Summary:" -ForegroundColor $ColorInfo
    
    $backupSize = (Get-ChildItem -Path $BackupDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
    Write-Host "  Total size: $(Format-FileSize $backupSize)"
    
    $timelineCount = (Get-ChildItem -Path "$BackupDir\TimelineItem" -Recurse -Filter "*.json" | Measure-Object).Count
    Write-Host "  TimelineItems: $timelineCount"
    
    $sampleCount = (Get-ChildItem -Path "$BackupDir\LocomotionSample" -Recurse -Filter "*.json.gz" | Measure-Object).Count
    Write-Host "  LocomotionSample files: $sampleCount"
    
    if (Test-Path "$BackupDir\Place") {
        $placeCount = (Get-ChildItem -Path "$BackupDir\Place" -Recurse -Filter "*.json" | Measure-Object).Count
        Write-Host "  Places: $placeCount"
    }
    
    Write-Host ""
    Write-Host "Filter range: $DateRange" -ForegroundColor $ColorInfo
}

function Run-PythonScript {
    param(
        [string]$BackupDir,
        [string]$OutputDir,
        [hashtable]$DateRange
    )
    
    # Find Python executable
    $pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } 
                 elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
                 else {
                    Write-Error2 "Python not found in PATH"
                    exit 1
                 }
    
    Write-Status "Python executable: $pythonCmd"
    
    # Build command arguments
    $args = @(
        "filter_backup_by_daterange.py",
        "--backup-dir", $BackupDir,
        "--output-dir", $OutputDir
    )
    
    # Add date arguments
    switch ($DateRange.Type) {
        "range" {
            $args += "--start", $DateRange.Start
            $args += "--end", $DateRange.End
        }
        "single" {
            $args += "--date", $DateRange.Date
        }
        "days" {
            $args += "--days", $DateRange.Days.ToString()
        }
    }
    
    Write-Host ""
    Write-Status "Starting filter operation..."
    Write-Host "Command: $pythonCmd $($args -join ' ')" -ForegroundColor Gray
    Write-Host ""
    
    # Run Python script
    & $pythonCmd @args
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error2 "Filter operation failed with exit code $LASTEXITCODE"
        exit 1
    }
    
    Write-Host ""
    Write-Success "Filter operation completed!"
}

# Main execution
Write-Title "LocoKit1 Backup Filter by Date Range"

# Determine if params were provided
if (-not $BackupDir) {
    $BackupDir = Prompt-ForBackupDir
}
else {
    if (-not (Validate-Directory $BackupDir "Backup directory")) {
        Write-Error2 "Invalid backup directory"
        exit 1
    }
}

if (-not $StartDate -and -not $EndDate -and -not $Days) {
    $DateRange = Prompt-ForDateRange
    if (-not $DateRange) {
        exit 1
    }
}
else {
    if ($StartDate -and $EndDate) {
        $DateRange = @{ Type = "range"; Start = $StartDate; End = $EndDate }
    }
    elseif ($Days) {
        $DateRange = @{ Type = "days"; Days = $Days }
    }
    else {
        Write-Error2 "Invalid date parameter combination"
        exit 1
    }
}

if (-not $OutputDir) {
    $OutputDir = Prompt-ForOutputDir
}

# Show summary
$dateRangeStr = switch ($DateRange.Type) {
    "range" { "$($DateRange.Start) to $($DateRange.End)" }
    "single" { "Full day: $($DateRange.Date)" }
    "days" { "Last $($DateRange.Days) days" }
}

Show-SummaryInfo $BackupDir $dateRangeStr

# Confirm before proceeding
Write-Host "Output directory: $OutputDir" -ForegroundColor $ColorInfo
Write-Host ""
$confirm = Read-Host "Proceed with filter operation? (y/n)"

if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Problem "Operation cancelled"
    exit 0
}

# Run the filter
Run-PythonScript $BackupDir $OutputDir $DateRange

Write-Host ""
Write-Status "Filtered backup location: $OutputDir"
Write-Host ""
