@echo off
REM Filter LocoKit1 Backup by Date Range (Windows Batch)
REM
REM This script provides an easy way to run the filter on Windows without PowerShell.
REM
REM Usage:
REM   filter_backup.bat
REM   (then follow the prompts)

setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo LocoKit1 Backup Filter by Date Range
echo ================================================================================
echo.

REM Check if Python is available
where python >nul 2>nul
if errorlevel 1 (
    where python3 >nul 2>nul
    if errorlevel 1 (
        echo [!] Python not found in PATH
        echo.
        echo Please install Python 3.7+ and add it to your PATH, then try again.
        echo https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
) else (
    set PYTHON_CMD=python
)

echo [*] Python: !PYTHON_CMD!
echo.

REM Prompt for backup directory
:prompt_backup_dir
echo Please enter the path to your LocoKit1 backup directory.
echo Example: c:\tmp\iCloud\iCloudDrive\iCloud~com~bigpaua~LearnerCoacher\Backups
echo.
set /p BACKUP_DIR="Backup directory: "

if "!BACKUP_DIR!"=="" (
    echo [!] Backup directory is required.
    goto prompt_backup_dir
)

if not exist "!BACKUP_DIR!" (
    echo [!] Directory does not exist: !BACKUP_DIR!
    goto prompt_backup_dir
)

if not exist "!BACKUP_DIR!\TimelineItem" (
    echo [!] Invalid backup directory - TimelineItem folder not found.
    echo This doesn't look like a valid LocoKit1 backup.
    goto prompt_backup_dir
)

echo [*] Backup directory: !BACKUP_DIR!
echo.

REM Prompt for output directory
:prompt_output_dir
set OUTPUT_DIR=
echo Please enter the output directory for the filtered backup.
echo (Press Enter to use ./filtered_backup)
echo.
set /p OUTPUT_DIR="Output directory: "

if "!OUTPUT_DIR!"=="" (
    set OUTPUT_DIR=filtered_backup
)

echo [*] Output directory: !OUTPUT_DIR!
echo.

REM Prompt for date range selection
:date_selection
echo Select how you want to specify the date range:
echo 1. Specific date range (e.g., Dec 15-31, 2024)
echo 2. Single date (full day, e.g., Dec 25, 2024)
echo 3. Last N days (e.g., last 7 days)
echo.
set /p DATE_CHOICE="Enter choice (1-3): "

if "!DATE_CHOICE!"=="1" goto date_range
if "!DATE_CHOICE!"=="2" goto single_date
if "!DATE_CHOICE!"=="3" goto last_days
echo [!] Invalid choice. Please enter 1, 2, or 3.
goto date_selection

:date_range
echo.
echo Enter the start date and time.
echo Format: YYYY-MM-DD HH:MM:SS  (including hours, minutes, seconds)
echo Example: 2024-12-15 00:00:00
echo.
set /p START_DATE="Start date/time: "

if "!START_DATE!"=="" (
    echo [!] Start date is required.
    goto date_range
)

REM Check if START_DATE contains space and colon
set START_NO_SPACE=!START_DATE: =!
set START_NO_COLON=!START_DATE::=!
if "!START_DATE!"=="!START_NO_SPACE!" (
    echo [!] Invalid format. Include the time. Example: 2024-12-15 00:00:00
    goto date_range
)
if "!START_DATE!"=="!START_NO_COLON!" (
    echo [!] Invalid format. Include the time. Example: 2024-12-15 00:00:00
    goto date_range
)

echo.
echo Enter the end date and time.
echo Format: YYYY-MM-DD HH:MM:SS  (including hours, minutes, seconds)
echo Example: 2024-12-31 23:59:59
echo.
set /p END_DATE="End date/time: "

if "!END_DATE!"=="" (
    echo [!] End date is required.
    goto date_range
)

REM Check if END_DATE contains space and colon
set END_NO_SPACE=!END_DATE: =!
set END_NO_COLON=!END_DATE::=!
if "!END_DATE!"=="!END_NO_SPACE!" (
    echo [!] Invalid format. Include the time. Example: 2024-12-31 23:59:59
    goto date_range
)
if "!END_DATE!"=="!END_NO_COLON!" (
    echo [!] Invalid format. Include the time. Example: 2024-12-31 23:59:59
    goto date_range
)

set DATE_ARGS=--start "!START_DATE!" --end "!END_DATE!"
goto run_filter

:single_date
echo.
echo Enter the date to filter.
echo Format: YYYY-MM-DD
echo Example: 2024-12-25
echo.
set /p SINGLE_DATE="Date: "

if "!SINGLE_DATE!"=="" (
    echo [!] Date is required.
    goto single_date
)

set DATE_ARGS=--date "!SINGLE_DATE!"
goto run_filter

:last_days
echo.
echo Enter number of days to include.
echo Example: 7 for last week
echo.
set /p DAYS="Days: "

if "!DAYS!"=="" (
    echo [!] Number of days is required.
    goto last_days
)

set DATE_ARGS=--days !DAYS!
goto run_filter

:run_filter
echo.
echo ================================================================================
echo Filter Configuration
echo ================================================================================
echo Backup directory: !BACKUP_DIR!
echo Output directory: !OUTPUT_DIR!
echo Date filter: !DATE_ARGS!
echo ================================================================================
echo.

:confirm
set /p CONFIRM="Proceed with filter operation? (y/n): "

if "!CONFIRM!"=="y" (
    goto execute
) else if "!CONFIRM!"=="Y" (
    goto execute
) else (
    echo [*] Operation cancelled.
    goto end
)

:execute
echo.
echo Starting filter operation...
echo.

!PYTHON_CMD! filter_backup_by_daterange.py ^
    --backup-dir "!BACKUP_DIR!" ^
    --output-dir "!OUTPUT_DIR!" ^
    !DATE_ARGS!

if errorlevel 1 (
    echo.
    echo [!] Filter operation failed.
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo [*] Filtered backup location: !OUTPUT_DIR!
    echo.
)

:end
pause
