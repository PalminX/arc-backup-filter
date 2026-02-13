# Arc Backup Filter

Filter Arc Timeline backup directories by date range, creating date-filtered copies while maintaining the complete directory structure.

(!) Note: This currently works on Arc Timeline (aka LocoKit1) backups only. 

## Overview

This tool creates a filtered copy of a LocoKit1/Arc backup, containing only data within a specified date range. Useful for:
- Creating test datasets
- Analyzing specific time periods
- Reducing backup size for sharing or analysis
- Creating period-specific archives

Output maintains the complete Arc backup structure (TimelineItem, LocomotionSample, Place directories), making it compatible with Arc-based analysis tools.

## Quick Start

### Windows Batch (Easiest)
```cmd
filter_backup.bat
```

### PowerShell
```powershell
.\filter_backup_by_daterange.ps1 -BackupDir "c:\backup" -Days 7
```

### Python Command Line
```bash
python filter_backup_by_daterange.py --backup-dir "c:\backup" --days 7
```

## Features

- Three interface options: Batch, PowerShell, or Python CLI
- Flexible date input: date range, single day, or "last N days"
- Maintains structure: timeline items, samples, and places all preserved
- Parallel processing for bucketed files
- Windows-native scripts included
- Cross-platform core (Python)

## Installation

### Requirements
- Python 3.7+
- A valid LocoKit1 backup directory with:
  - TimelineItem/ folder (hex-bucketed)
  - LocomotionSample/ folder (week-bucketed .json.gz files)
  - Place/ folder (optional but recommended)

### Setup
1. Ensure Python is in your PATH:
   ```powershell
   python --version
   ```

2. Clone or download this repository.

3. Run the script of your choice:
   - Batch: filter_backup.bat
   - PowerShell: .\filter_backup_by_daterange.ps1
   - Python: python filter_backup_by_daterange.py --help

## Usage Examples

### Filter by Date Range
```powershell
python filter_backup_by_daterange.py `
  --backup-dir "C:\backup" `
  --start "2024-12-15 00:00:00" `
  --end "2024-12-31 23:59:59" `
  --output-dir "C:\filtered_backup"
```

### Filter Last 7 Days
```powershell
python filter_backup_by_daterange.py --backup-dir "C:\backup" --days 7
```

### Filter Single Day
```powershell
python filter_backup_by_daterange.py --backup-dir "C:\backup" --date "2024-12-25"
```

### Interactive (PowerShell or Batch)
```powershell
.\filter_backup_by_daterange.ps1
```

## Command-Line Options

```
usage: filter_backup_by_daterange.py [-h] --backup-dir BACKUP_DIR
                                     [--output-dir OUTPUT_DIR]
                                     (--start START | --date DATE | --days DAYS)
                                     [--end END]

Filter LocoKit1 backup by date range

options:
  --backup-dir BACKUP_DIR     Path to LocoKit1 backup root directory (required)
  --output-dir OUTPUT_DIR     Output directory (default: ./filtered_backup)
  --start START               Start date/time (YYYY-MM-DD HH:MM:SS)
  --end END                   End date/time (YYYY-MM-DD HH:MM:SS)
  --date DATE                 Single date to filter (YYYY-MM-DD)
  --days DAYS                 Number of days back from today
```

## Date Format

Use ISO format with time: YYYY-MM-DD HH:MM:SS

Examples:
- 2024-12-15 00:00:00
- 2024-12-31 23:59:59
- 2025-02-13 14:30:45

## Output Structure

```
filtered_backup/
├── TimelineItem/          # Hex-bucketed (00-FF)
│   ├── 00/
│   │   ├── UUID1.json
│   │   └── UUID2.json
│   └── FF/
│       └── UUID3.json
├── LocomotionSample/      # Week-bucketed .json.gz
│   ├── 2024-W50.json.gz
│   └── 2024-W51.json.gz
└── Place/                 # Hex-bucketed
    ├── A/
    │   └── PLACE_UUID.json
    └── B/
        └── PLACE_UUID.json
```

## Filtering Rules

- TimelineItems: copied if they overlap the date range (start <= filter end and end >= filter start)
- LocomotionSamples: copied if timestamp is within the date range
- Places: copied only if referenced by filtered TimelineItems

## Performance

Typical processing times (varies by backup size and date range):
- 1-7 days: 5-30 seconds
- 1 month: 30-120 seconds
- 1 year: 2-10 minutes

The script uses parallel processing (16 workers) for TimelineItem buckets.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Python not found | Install Python 3.7+ from https://www.python.org and select "Add Python to PATH" |
| "TimelineItem directory not found" | Verify backup path is correct and contains TimelineItem/ folder |
| PowerShell execution error | Run `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process` |
| No files in output | Try a wider date range; start with --days 30 |
| Out of disk space | Ensure output location has sufficient free space for filtered data |

## Logs

```
[*] Filtering TimelineItems from 2024-12-15 00:00:00 to 2024-12-31 23:59:59
[*] Filtered 245 TimelineItems from 8 buckets
[*] Found 42 unique place IDs
[*] Processing 5 week files
[*] Filtered 1,203 LocomotionSamples from 5 week files
[*] Copying 42 place records
[✓] Copied 38 place records
[✓] Filter operation completed successfully!
  TimelineItems: 245
  LocomotionSamples: 1,203
  Places: 38
```

## Notes

- The original backup is never modified; a new filtered copy is created
- Empty/corrupted files are skipped with warnings logged
- Places are only copied if referenced by filtered TimelineItems
- All operations are read-only on the source backup
- Output directory is created if it doesn't exist

## Technical Details

### Supported Backup Format

The tool works with LocoKit1 backups in the Arc iCloud format:
- TimelineItem: hex-bucketed JSON files (00-FF)
- LocomotionSample: ISO-week-bucketed gzip JSON files (YYYY-Wnn.json.gz)
- Place: optional hex-bucketed place metadata

### Python Version Support

- Python 3.7+
- Uses only standard library (no external dependencies)

### Parallel Processing

- TimelineItems: 16 parallel workers for efficient I/O
- LocomotionSamples: sequential processing
- Places: sequential processing

## Contributing

Found a bug or want to suggest a feature? Please use the Issues tab on GitHub.

## License

Apache License 2.0 — See LICENSE file for details.

## Attribution

Created with GitHub Copilot.

## Related

- Arc App: https://arc-app.com/
- LocoKit2: https://github.com/sobri909/LocoKit2

---

Version: 1.0
Last Updated: February 2025
Tested on: Windows 11, Python 3.11
