# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-13

### Added
- Auto-detection of LocoKit1 vs LocoKit2 backup formats
- LocoKit2 support for items, samples, and places backups
- LocoKit2 output structure documentation

### Changed
- Python filter now handles LocoKit2 monthly items and bucketed places
- Batch and PowerShell validation now accepts LocoKit2 directory names
- Batch script normalizes trailing backslashes in input/output paths

## [1.0.0] - 2025-02-13

### Added
- Initial release
- Python script for filtering Arc/LocoKit1 backups by date range
- Windows batch interface (filter_backup.bat)
- PowerShell wrapper script with interactive mode
- Support for three date input methods:
  - Specific date range (YYYY-MM-DD HH:MM:SS to YYYY-MM-DD HH:MM:SS)
  - Single date (YYYY-MM-DD, full day)
  - Last N days (e.g., --days 7)
- Complete documentation with examples
- Apache 2.0 license

### Features
- Parallel processing of TimelineItem buckets (16 workers)
- Preserves full Arc backup directory structure
- Maintains place metadata references
- Handles corrupted/empty files gracefully
- Comprehensive error handling and validation
- Detailed logging for diagnostics

### Tested
- Windows 11, Python 3.11
- Batch and PowerShell on Windows Command Prompt
- Date validation and format checking
- Various backup sizes and date ranges
