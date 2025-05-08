#!/usr/bin/env python3
"""
Photo Timestamp Updater

This script updates the EXIF timestamp metadata of photos based on timestamps
embedded in their filenames (format: YYYYMMDDhhmmss).

Requirements:
- Python 3.6+
- piexif (install with: pip install piexif)
- Pillow (install with: pip install Pillow)
"""

import os
import re
import sys
import time
import datetime
import argparse
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import piexif
    from PIL import Image
except ImportError:
    print("Required libraries not installed. Please run:")
    print("pip install piexif Pillow")
    sys.exit(1)


def extract_timestamp_from_filename(filename: str) -> Optional[datetime.datetime]:
    """
    Extract timestamp from filename with format YYYYMMDDhhmmss.
    Returns None if no timestamp is found.
    """
    # Match YYYYMMDD followed by hhmmss (with optional seconds)
    match = re.search(r'(\d{8})(\d{4})(\d{2})?', filename)
    if not match:
        return None
    
    date_part = match.group(1)
    time_part = match.group(2)
    seconds_part = match.group(3) or "00"  # Default to 00 seconds if not provided
    
    try:
        year = int(date_part[0:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[0:2])
        minute = int(time_part[2:4])
        second = int(seconds_part)
        
        return datetime.datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def format_exif_datetime(dt: datetime.datetime) -> str:
    """Format datetime object to EXIF datetime string format."""
    return dt.strftime("%Y:%m:%d %H:%M:%S")


def update_photo_timestamps(file_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Update EXIF timestamps in the photo file based on its filename.
    Returns (success, message) tuple.
    """
    filename = file_path.name
    timestamp = extract_timestamp_from_filename(filename)
    
    if not timestamp:
        return False, f"Could not extract timestamp from filename: {filename}"
    
    # Ensure the file is a supported image
    try:
        img = Image.open(file_path)
    except Exception as e:
        return False, f"Error opening image: {e}"
    
    # Format timestamp for EXIF
    exif_timestamp = format_exif_datetime(timestamp)
    
    try:
        # Get existing EXIF data or create new
        try:
            exif_dict = piexif.load(img.info.get('exif', b''))
        except Exception:
            exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
        
        # Update all date-related EXIF tags
        date_tags = [
            (piexif.ExifIFD.DateTimeOriginal, exif_timestamp),
            (piexif.ExifIFD.DateTimeDigitized, exif_timestamp),
            (piexif.ImageIFD.DateTime, exif_timestamp)
        ]
        
        for tag, value in date_tags:
            exif_dict['Exif'][tag] = value.encode('ascii')
        
        if '0th' not in exif_dict:
            exif_dict['0th'] = {}
        exif_dict['0th'][piexif.ImageIFD.DateTime] = exif_timestamp.encode('ascii')
        
        # Prepare EXIF bytes
        exif_bytes = piexif.dump(exif_dict)
        
        if dry_run:
            return True, f"Would update timestamp for {filename} to {exif_timestamp}"
        
        # Save with updated EXIF
        img.save(file_path, exif=exif_bytes)
        
        # Also update file modification time
        unix_time = time.mktime(timestamp.timetuple())
        os.utime(file_path, (unix_time, unix_time))
        
        return True, f"Updated timestamp for {filename} to {exif_timestamp}"
    
    except Exception as e:
        return False, f"Error updating EXIF data for {filename}: {e}"
    finally:
        img.close()


def process_directory(directory: Path, recursive: bool = False, 
                     extensions: List[str] = None, dry_run: bool = False) -> Tuple[int, int]:
    """
    Process all images in a directory.
    Returns (success_count, failure_count) tuple.
    """
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.heic']
    
    success_count = 0
    failure_count = 0
    
    # Get all files in directory
    if recursive:
        files = [p for p in directory.glob('**/*') if p.is_file()]
    else:
        files = [p for p in directory.iterdir() if p.is_file()]
    
    # Filter by extensions
    image_files = [f for f in files if f.suffix.lower() in extensions]
    
    print(f"Found {len(image_files)} image files to process")
    
    for i, file_path in enumerate(image_files, 1):
        print(f"Processing [{i}/{len(image_files)}] {file_path.name}...", end=" ")
        success, message = update_photo_timestamps(file_path, dry_run)
        print(message)
        
        if success:
            success_count += 1
        else:
            failure_count += 1
    
    return success_count, failure_count


def main():
    parser = argparse.ArgumentParser(description='Update photo timestamps based on filename.')
    parser.add_argument('directory', type=str, help='Directory containing image files')
    parser.add_argument('-r', '--recursive', action='store_true', 
                        help='Recursively process subdirectories')
    parser.add_argument('-e', '--extensions', type=str, default='.jpg,.jpeg,.png,.tiff,.tif,.heic',
                        help='Comma-separated list of file extensions to process')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='Perform a dry run without modifying files')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        print(f"Error: {args.directory} is not a valid directory")
        return 1
    
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                 for ext in args.extensions.split(',')]
    
    print(f"{'DRY RUN - ' if args.dry_run else ''}Processing images in {directory}")
    print(f"File extensions: {', '.join(extensions)}")
    print(f"Recursive mode: {'Yes' if args.recursive else 'No'}")
    
    success, failure = process_directory(
        directory, 
        recursive=args.recursive,
        extensions=extensions,
        dry_run=args.dry_run
    )
    
    print(f"\nSummary: {success} succeeded, {failure} failed")
    return 0 if failure == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
