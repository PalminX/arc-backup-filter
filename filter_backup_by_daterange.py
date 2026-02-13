#!/usr/bin/env python3
r"""
Filter LocoKit1/LocoKit2 Backup by Date Range

Creates a filtered copy of a LocoKit1 or LocoKit2 backup containing only data within a specified
date range. Maintains the full directory structure:
- LocoKit1: TimelineItem, LocomotionSample, Place
- LocoKit2: items, samples, places

Usage:
  python filter_backup_by_daterange.py ^
    --backup-dir "c:\tmp\iCloud\iCloudDrive\iCloud~com~bigpaua~LearnerCoacher\Backups" ^
    --start "2024-12-15 00:00:00" ^
    --end "2024-12-31 23:59:59" ^
    --output-dir "c:\tmp\filtered_backup"

  # Or with defaults (filters last 7 days to ./filtered_backup)
  python filter_backup_by_daterange.py ^
    --backup-dir "c:\path\to\backup"
"""

import json
import gzip
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set, Dict, Optional, Tuple
import argparse
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupFilter:
    """Filters and copies LocoKit1/LocoKit2 backup data by date range."""
    
    def __init__(self, backup_dir: str, output_dir: str):
        """
        Initialize the filter.
        
        Args:
            backup_dir: Path to source Arc/LocoKit1 or LocoKit2 backup
            output_dir: Path to output directory (will be created)
        """
        self.backup_dir = Path(backup_dir)
        self.output_dir = Path(output_dir)
        self.backup_type = self._detect_backup_type()
        
        if self.backup_type == "locokit1":
            self.timeline_item_dir = self.backup_dir / "TimelineItem"
            self.locomotion_sample_dir = self.backup_dir / "LocomotionSample"
            self.place_dir = self.backup_dir / "Place"
            
            if not self.timeline_item_dir.exists():
                raise ValueError(f"TimelineItem directory not found: {self.timeline_item_dir}")
            if not self.locomotion_sample_dir.exists():
                raise ValueError(f"LocomotionSample directory not found: {self.locomotion_sample_dir}")
            
            self.output_timeline_dir = self.output_dir / "TimelineItem"
            self.output_sample_dir = self.output_dir / "LocomotionSample"
            self.output_place_dir = self.output_dir / "Place"
        else:
            self.timeline_item_dir = self.backup_dir / "items"
            self.locomotion_sample_dir = self.backup_dir / "samples"
            self.place_dir = self.backup_dir / "places"
            
            if not self.timeline_item_dir.exists():
                raise ValueError(f"items directory not found: {self.timeline_item_dir}")
            if not self.locomotion_sample_dir.exists():
                raise ValueError(f"samples directory not found: {self.locomotion_sample_dir}")
            if not self.place_dir.exists():
                logger.warning("places directory not found; place metadata will be skipped")
            
            self.output_timeline_dir = self.output_dir / "items"
            self.output_sample_dir = self.output_dir / "samples"
            self.output_place_dir = self.output_dir / "places"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_timeline_dir.mkdir(parents=True, exist_ok=True)
        self.output_sample_dir.mkdir(parents=True, exist_ok=True)
        self.output_place_dir.mkdir(parents=True, exist_ok=True)

    def _detect_backup_type(self) -> str:
        """Detect whether backup directory is LocoKit1 or LocoKit2."""
        has_locokit1 = (self.backup_dir / "TimelineItem").exists() and (self.backup_dir / "LocomotionSample").exists()
        has_locokit2 = (self.backup_dir / "items").exists() and (self.backup_dir / "samples").exists()

        if has_locokit2 and not has_locokit1:
            return "locokit2"
        if has_locokit1 and not has_locokit2:
            return "locokit1"
        if has_locokit1 and has_locokit2:
            logger.warning("Both LocoKit1 and LocoKit2 structures detected; defaulting to LocoKit2")
            return "locokit2"

        raise ValueError(
            "Backup format not recognized. Expected LocoKit1 (TimelineItem/LocomotionSample) "
            "or LocoKit2 (items/samples) directories."
        )
    
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string to naive datetime (UTC assumed)."""
        if not date_str:
            return None
        
        try:
            # Handle both space and T separator
            normalized = date_str.replace(' ', 'T')
            # Remove timezone info
            if 'Z' in normalized:
                normalized = normalized.replace('Z', '')
            elif '+' in normalized:
                normalized = normalized.split('+')[0]
            elif normalized.count('-') > 2:  # has negative timezone
                parts = normalized.split('-')
                normalized = '-'.join(parts[:3])  # keep only date parts
            return datetime.fromisoformat(normalized)
        except (ValueError, AttributeError):
            return None
    
    def filter_timeline_items(self, start_date: str, end_date: str) -> Tuple[Set[str], int]:
        """
        Filter and copy TimelineItems within date range.
        
        Returns:
            Tuple of (place IDs referenced by filtered items, filtered item count)
        
        Args:
            start_date: ISO datetime string (YYYY-MM-DD HH:MM:SS)
            end_date: ISO datetime string (YYYY-MM-DD HH:MM:SS)
        """
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)
        
        if not start_dt or not end_dt:
            raise ValueError("Invalid date format. Use: YYYY-MM-DD HH:MM:SS")
        
        if start_dt > end_dt:
            raise ValueError("Start date cannot be after end date")
        
        logger.info(f"Filtering TimelineItems from {start_date} to {end_date}")
        
        place_ids: Set[str] = set()
        item_count = 0

        if self.backup_type == "locokit1":
            bucket_count = 0
            bucket_dirs = sorted([d for d in self.timeline_item_dir.iterdir() if d.is_dir()])

            for bucket_dir in bucket_dirs:
                bucket_name = bucket_dir.name
                bucket_items = 0

                output_bucket = self.output_timeline_dir / bucket_name
                output_bucket.mkdir(exist_ok=True)

                for item_file in bucket_dir.glob("*.json"):
                    try:
                        if item_file.stat().st_size == 0:
                            continue

                        with open(item_file, 'r', encoding='utf-8') as f:
                            item = json.load(f)

                        item_start = self._parse_date(item.get('startDate'))
                        item_end = self._parse_date(item.get('endDate'))

                        if item_start and item_end and item_start <= end_dt and item_end >= start_dt:
                            output_file = output_bucket / item_file.name
                            shutil.copy2(item_file, output_file)

                            if item.get('isVisit') and 'placeId' in item:
                                place_ids.add(item['placeId'])

                            bucket_items += 1
                            item_count += 1

                    except json.JSONDecodeError:
                        logger.warning(f"Skipping corrupted JSON: {item_file.name}")
                    except Exception as e:
                        logger.warning(f"Error processing {item_file.name}: {e}")

                if bucket_items > 0:
                    logger.debug(f"Bucket {bucket_name}: {bucket_items} items")
                    bucket_count += 1

            logger.info(f"Filtered {item_count} TimelineItems from {bucket_count} buckets")
        else:
            month_files = self._iter_locokit2_item_files_for_range(start_dt, end_dt)
            month_file_count = 0

            for item_file in month_files:
                items = self._read_locokit2_item_file(item_file)
                if not items:
                    continue

                filtered_items = []
                for item in items:
                    base = item.get('base') or {}
                    item_start = self._parse_date(base.get('startDate') or item.get('startDate'))
                    item_end = self._parse_date(base.get('endDate') or item.get('endDate'))

                    if item_start and item_end and item_start <= end_dt and item_end >= start_dt:
                        filtered_items.append(item)
                        place_id = self._extract_place_id(item)
                        if place_id:
                            place_ids.add(place_id)

                if filtered_items:
                    output_file = self.output_timeline_dir / item_file.name
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(filtered_items, f)

                    item_count += len(filtered_items)
                    month_file_count += 1

            logger.info(f"Filtered {item_count} TimelineItems from {month_file_count} month files")

        logger.info(f"Found {len(place_ids)} unique place IDs")

        return place_ids, item_count
    
    def filter_locomotion_samples(self, start_date: str, end_date: str) -> int:
        """
        Filter and copy LocomotionSamples within date range.
        
        Returns:
            Count of samples copied
        """
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)
        
        logger.info(f"Filtering LocomotionSamples from {start_date} to {end_date}")
        
        sample_count = 0
        week_count = 0
        
        # Get all week files that overlap the date range
        week_files = self._get_week_files_for_range(start_dt, end_dt)
        
        logger.info(f"Processing {len(week_files)} week files")
        
        for week_file in week_files:
            try:
                # Skip empty/corrupted files
                if week_file.stat().st_size == 0:
                    continue
                
                # Read week file
                with gzip.open(week_file, 'rt', encoding='utf-8') as f:
                    samples = json.load(f)
                
                # Filter samples by date
                filtered_samples = []
                for sample in samples:
                    sample_date = self._parse_date(sample.get('date'))
                    if sample_date and start_dt <= sample_date <= end_dt:
                        filtered_samples.append(sample)
                
                if filtered_samples:
                    # Write filtered samples to output
                    output_file = self.output_sample_dir / week_file.name
                    with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                        json.dump(filtered_samples, f)
                    
                    sample_count += len(filtered_samples)
                    week_count += 1
                    logger.debug(f"Week {week_file.name}: {len(filtered_samples)} samples")
            
            except (gzip.BadGzipFile, EOFError):
                logger.warning(f"Corrupted gzip file: {week_file.name}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in week file: {week_file.name}")
            except Exception as e:
                logger.warning(f"Error processing {week_file.name}: {e}")
        
        logger.info(f"Filtered {sample_count} LocomotionSamples from {week_count} week files")
        return sample_count
    
    def _get_week_files_for_range(self, start_dt: datetime, end_dt: datetime) -> List[Path]:
        """Get list of week files that cover the date range."""
        week_files = []
        all_files = sorted(self.locomotion_sample_dir.glob("*.json.gz"))
        
        for week_file in all_files:
            # Parse week file name: YYYY-Wnn.json.gz
            try:
                name_parts = week_file.stem.replace('.json', '').split('-W')
                if len(name_parts) != 2:
                    continue
                
                year = int(name_parts[0])
                week = int(name_parts[1])
                
                # ISO week date: Get Monday of that week
                jan4 = datetime(year, 1, 4)
                week1_monday = jan4 - timedelta(days=jan4.weekday())
                week_start = week1_monday + timedelta(weeks=week - 1)
                week_end = week_start + timedelta(days=7)
                
                # Include if week overlaps date range
                if week_start <= end_dt and week_end >= start_dt:
                    week_files.append(week_file)
            
            except (ValueError, IndexError):
                logger.warning(f"Could not parse week file name: {week_file.name}")
        
        return week_files

    def _iter_locokit2_item_files_for_range(self, start_dt: datetime, end_dt: datetime) -> List[Path]:
        files = []
        current = datetime(start_dt.year, start_dt.month, 1)
        end_marker = datetime(end_dt.year, end_dt.month, 1)
        while current <= end_marker:
            name = f"{current.year:04d}-{current.month:02d}.json"
            path = self.timeline_item_dir / name
            if path.exists():
                files.append(path)
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        return files

    def _read_locokit2_item_file(self, item_file: Path) -> List[Dict]:
        try:
            if item_file.stat().st_size == 0:
                return []
            with open(item_file, 'r', encoding='utf-8') as f:
                items = json.load(f)
            return items if isinstance(items, list) else []
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading item file {item_file.name}: {e}")
            return []

    def _extract_place_id(self, item: Dict) -> Optional[str]:
        base = item.get('base') or {}
        visit = item.get('visit') or {}
        place = item.get('place') or {}

        for candidate in (
            item.get('placeId'),
            base.get('placeId'),
            visit.get('placeId') if isinstance(visit, dict) else None,
            place.get('id') if isinstance(place, dict) else None,
        ):
            if isinstance(candidate, str) and candidate:
                return candidate
        return None
    
    def copy_places(self, place_ids: Set[str]) -> int:
        """
        Copy Place files for the given place IDs.
        
        Returns:
            Count of places copied
        """
        if not self.place_dir.exists():
            logger.warning("Place directory not found in backup")
            return 0

        logger.info(f"Copying {len(place_ids)} place records")

        place_count = 0

        if self.backup_type == "locokit1":
            for place_id in place_ids:
                try:
                    bucket = place_id[0].upper()
                    source_file = self.place_dir / bucket / f"{place_id}.json"

                    if not source_file.exists():
                        logger.debug(f"Place file not found: {place_id}")
                        continue

                    output_bucket = self.output_place_dir / bucket
                    output_bucket.mkdir(exist_ok=True)

                    output_file = output_bucket / f"{place_id}.json"
                    shutil.copy2(source_file, output_file)
                    place_count += 1

                except Exception as e:
                    logger.warning(f"Error copying place {place_id}: {e}")
        else:
            bucket_ids = sorted({pid[0].upper() for pid in place_ids if isinstance(pid, str) and pid})
            place_id_set = {pid for pid in place_ids if isinstance(pid, str) and pid}

            for bucket in bucket_ids:
                source_file = self.place_dir / f"{bucket}.json"
                if not source_file.exists():
                    logger.debug(f"Place bucket file not found: {bucket}.json")
                    continue

                try:
                    with open(source_file, 'r', encoding='utf-8') as f:
                        places = json.load(f)
                    if not isinstance(places, list):
                        continue

                    filtered_places = [p for p in places if p.get('id') in place_id_set]
                    if not filtered_places:
                        continue

                    output_file = self.output_place_dir / f"{bucket}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(filtered_places, f)

                    place_count += len(filtered_places)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Error reading place bucket {bucket}: {e}")

        logger.info(f"Copied {place_count} place records")
        return place_count
    
    def run(self, start_date: str, end_date: str) -> Dict[str, int]:
        """
        Run the full filter operation.
        
        Returns:
            Dictionary with counts of items, samples, and places
        """
        logger.info("=" * 70)
        logger.info(f"Starting backup filter operation")
        logger.info(f"Source: {self.backup_dir}")
        logger.info(f"Output: {self.output_dir}")
        logger.info(f"Detected backup type: {self.backup_type}")
        logger.info("=" * 70)
        
        try:
            # Step 1: Filter TimelineItems
            place_ids, timeline_count = self.filter_timeline_items(start_date, end_date)
            
            # Step 2: Filter LocomotionSamples
            sample_count = self.filter_locomotion_samples(start_date, end_date)
            
            # Step 3: Copy Places
            place_count = self.copy_places(place_ids)
            
            logger.info("=" * 70)
            logger.info("✓ Filter operation completed successfully!")
            logger.info(f"  TimelineItems: {timeline_count}")
            logger.info(f"  LocomotionSamples: {sample_count}")
            logger.info(f"  Places: {place_count}")
            logger.info(f"  Output directory: {self.output_dir}")
            logger.info("=" * 70)
            
            return {
                'timeline_items': timeline_count,
                'samples': sample_count,
                'places': place_count
            }
        
        except Exception as e:
            logger.error(f"✗ Filter operation failed: {e}")
            raise


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Filter LocoKit1/LocoKit2 backup by date range',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Filter specific date range
  python filter_backup_by_daterange.py ^
    --backup-dir "c:\\backup" ^
    --start "2024-12-15 00:00:00" ^
    --end "2024-12-31 23:59:59" ^
    --output-dir "c:\\filtered"
  
  # Filter last 7 days
  python filter_backup_by_daterange.py ^
    --backup-dir "c:\\backup" ^
    --days 7
  
  # Filter specific day
  python filter_backup_by_daterange.py ^
    --backup-dir "c:\\backup" ^
    --date "2024-12-25"
        '''
    )
    
    parser.add_argument(
        '--backup-dir',
        type=str,
        required=True,
        help='Path to LocoKit1 or LocoKit2 backup root directory'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./filtered_backup',
        help='Output directory for filtered backup (default: ./filtered_backup)'
    )
    
    # Date input options (mutually exclusive)
    date_group = parser.add_mutually_exclusive_group(required=True)
    
    date_group.add_argument(
        '--start',
        type=str,
        help='Start date/time (format: YYYY-MM-DD HH:MM:SS)'
    )
    
    date_group.add_argument(
        '--date',
        type=str,
        help='Single date to filter (format: YYYY-MM-DD, will use full day)'
    )
    
    date_group.add_argument(
        '--days',
        type=int,
        help='Number of days back from today (e.g., 7 for last week)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='End date/time (format: YYYY-MM-DD HH:MM:SS). Required with --start.'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Determine date range based on arguments
    if args.start:
        if not args.end:
            parser = argparse.ArgumentParser()
            parser.error("--end is required when using --start")
        start_date = args.start
        end_date = args.end
    
    elif args.date:
        start_date = f"{args.date} 00:00:00"
        end_date = f"{args.date} 23:59:59"
    
    elif args.days:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=args.days)
        start_date = start_dt.strftime("%Y-%m-%d 00:00:00")
        end_date = end_dt.strftime("%Y-%m-%d 23:59:59")
    
    else:
        parser = argparse.ArgumentParser()
        parser.error("Must specify --start/--end, --date, or --days")
    
    logger.info(f"Date range: {start_date} to {end_date}")
    
    # Run filter
    filter_obj = BackupFilter(args.backup_dir, args.output_dir)
    results = filter_obj.run(start_date, end_date)
    
    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        exit(1)
