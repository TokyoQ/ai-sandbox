#!/usr/bin/env python3
"""
Photo Timestamp Updater

This script updates the EXIF timestamp metadata of photos based on timestamps
embedded in their filenames (format: YYYYMMDDhhmmss).

Requirements:
- Python 3.6+
- piexif (install with: pip install piexif)
- Pillow (install with: pip install Pillow)

Note: For handling files with special characters or spaces in filenames or paths,
enclose the path in quotes when running the script:
  python photo_timestamp_updater.py "/path/with spaces/to/my photos"
"""

import os
import re
import sys
import time
import datetime
import argparse
import platform
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import piexif
    from PIL import Image
except ImportError:
    print("Required libraries not installed. Please run:")
    print("pip install piexif Pillow")
    sys.exit(1)

# Try to import platform-specific modules for creation time
try:
    if platform.system() == 'Windows':
        import win32file
        import win32con
        HAS_CREATION_TIME = True
    elif platform.system() == 'Darwin':  # macOS
        import stat
        from ctypes import cdll, c_char_p, c_int, c_double
        try:
            libc = cdll.LoadLibrary('libc.dylib')
            HAS_CREATION_TIME = True
        except:
            HAS_CREATION_TIME = False
    else:  # Linux and others
        try:
            import os
            import ctypes
            libc = ctypes.CDLL('libc.so.6')
            HAS_CREATION_TIME = 'birth_time' in dir(os.stat_result)
        except:
            HAS_CREATION_TIME = False
except ImportError:
    HAS_CREATION_TIME = False


def set_file_times(file_path: Path, timestamp: datetime.datetime) -> bool:
    """
    Set both modification and creation time of a file.
    Returns True if successful, False otherwise.
    """
    unix_time = time.mktime(timestamp.timetuple())
    
    # Always set the modification time
    try:
        os.utime(file_path, (unix_time, unix_time))
    except Exception as e:
        print(f"Warning: Failed to set modification time: {e}")
        return False
    
    # Try to set creation time based on platform
    if HAS_CREATION_TIME:
        try:
            if platform.system() == 'Windows':
                # Windows implementation
                handle = win32file.CreateFile(
                    str(file_path),
                    win32file.GENERIC_WRITE,
                    0, None, 
                    win32con.OPEN_EXISTING,
                    0, None
                )
                win32file.SetFileTime(
                    handle,
                    timestamp,  # Creation time
                    None,       # Last access time (leave unchanged)
                    timestamp   # Last write time
                )
                handle.close()
            elif platform.system() == 'Darwin':  # macOS
                # Convert path to bytes
                path_bytes = str(file_path).encode('utf-8')
                
                # Create C-compatible types
                c_path = c_char_p(path_bytes)
                c_time = c_double(unix_time)
                
                # macOS: Call setattrlist to set creation time
                # This requires special permissions or admin rights
                try:
                    # Use setfile command as alternative
                    os.system(f"SetFile -d '{timestamp.strftime('%m/%d/%Y %H:%M:%S')}' '{file_path}'")
                except:
                    print(f"Warning: Failed to set creation time on macOS for {file_path.name}")
            else:  # Linux and others with birth time support
                if 'birth_time' in dir(os.stat_result):
                    try:
                        # Some Linux filesystems support birthtime
                        # Attempt to use it via lower level calls
                        # This varies by filesystem and may not work everywhere
                        # For ext4 with recent kernels, this might work
                        os.system(f"touch -t {timestamp.strftime('%Y%m%d%H%M.%S')} '{file_path}'")
                    except:
                        print(f"Warning: Failed to set creation time on Linux for {file_path.name}")
        except Exception as e:
            print(f"Warning: Failed to set creation time: {e}")
            return False
    else:
        if platform.system() == 'Darwin':  # macOS fallback
            try:
                # Try using SetFile command which is available on most macOS systems
                date_str = timestamp.strftime('%m/%d/%Y %H:%M:%S')
                os.system(f"SetFile -d '{date_str}' '{file_path}'")
            except:
                print(f"Warning: Failed to set creation time using SetFile for {file_path.name}")
                
    return True


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
    
    # Format timestamp for EXIF
    exif_timestamp = format_exif_datetime(timestamp)
    
    if dry_run:
        return True, f"Would update timestamp for {filename} to {exif_timestamp}"
    
    # Method 1: Try using piexif directly on the file
    try:
        # First try a more direct approach with piexif
        try:
            exif_dict = piexif.load(str(file_path))
        except Exception:
            exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
        
        # Update all date-related EXIF tags
        if 'Exif' not in exif_dict:
            exif_dict['Exif'] = {}
        if '0th' not in exif_dict:
            exif_dict['0th'] = {}
            
        # Set DateTime tags
        exif_dict['0th'][piexif.ImageIFD.DateTime] = exif_timestamp.encode('ascii')
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_timestamp.encode('ascii')
        exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = exif_timestamp.encode('ascii')
        
        # Insert the EXIF data
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(file_path))
        
        # Update file modification and creation times
        set_file_times(file_path, timestamp)
        
        return True, f"Updated timestamp for {filename} to {exif_timestamp}"
        
    except Exception as e:
        # If direct piexif method failed, try with PIL as fallback
        try:
            img = Image.open(file_path)
            
            # Create minimal EXIF dictionary with just the date tags
            exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
            exif_dict['0th'][piexif.ImageIFD.DateTime] = exif_timestamp.encode('ascii')
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_timestamp.encode('ascii')
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = exif_timestamp.encode('ascii')
            
            # Dump to bytes
            exif_bytes = piexif.dump(exif_dict)
            
            # Save to a temporary file first
            temp_file = str(file_path) + ".tmp"
            img.save(temp_file, exif=exif_bytes)
            img.close()
            
            # Replace original with temporary file
            os.replace(temp_file, file_path)
            
            # Update file modification and creation times
            set_file_times(file_path, timestamp)
            
            return True, f"Updated timestamp for {filename} to {exif_timestamp} (fallback method)"
            
        except Exception as e2:
            return False, f"Error updating EXIF data for {filename}: {e}; Fallback also failed: {e2}"


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