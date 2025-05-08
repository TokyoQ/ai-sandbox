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
    import shlex  # Add this for proper shell escaping
except ImportError:
    print("Required libraries not installed. Please run:")
    print("pip install piexif Pillow")
    sys.exit(1)

# Try to import platform-specific modules for creation time
if platform.system() == 'Windows':
    try:
        import win32file
        import win32con
        import pywintypes
        HAS_CREATION_TIME = True
    except ImportError:
        print("Warning: win32file/win32con modules not available. Creation time cannot be set on Windows.")
        print("Please install pywin32: pip install pywin32")
        HAS_CREATION_TIME = False
elif platform.system() == 'Darwin':  # macOS
    # Check if SetFile command is available
    result = os.system("which SetFile > /dev/null 2>&1")
    if result == 0:
        HAS_CREATION_TIME = True
    else:
        print("Warning: SetFile command not found. Creation time may not be set correctly on macOS.")
        print("Install Apple Developer Tools for full functionality.")
        HAS_CREATION_TIME = True  # We'll still try with touch command
else:  # Linux and others
    # We'll use touch command which works on most systems
    HAS_CREATION_TIME = True


def set_file_times(file_path, timestamp: datetime.datetime) -> bool:
    """
    Set both modification and creation time of a file.
    Returns True if successful, False otherwise.
    """
    unix_time = time.mktime(timestamp.timetuple())
    str_path = str(file_path)
    
    # Always set the modification time
    try:
        os.utime(str_path, (unix_time, unix_time))
    except Exception as e:
        print(f"Warning: Failed to set modification time: {e}")
        return False
    
    # Platform-specific creation time handling
    system = platform.system()
    
    if system == 'Windows':
        try:
            # Windows implementation
            handle = win32file.CreateFile(
                str_path,
                win32file.GENERIC_WRITE,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None, 
                win32con.OPEN_EXISTING,
                win32con.FILE_ATTRIBUTE_NORMAL,
                None
            )
            
            # Convert datetime to Windows FileTime format
            win_time = timestamp
            
            # Set the file times
            win32file.SetFileTime(
                handle,
                win_time,      # Creation time
                None,          # Last access time (leave unchanged)
                win_time       # Last write time
            )
            handle.Close()
            return True
            
        except Exception as e:
            print(f"Warning: Failed to set creation time on Windows: {e}")
    
    elif system == 'Darwin':  # macOS
        try:
            # Format date for SetFile command (MM/DD/YYYY HH:MM:SS)
            date_str = timestamp.strftime('%m/%d/%Y %H:%M:%S')
            
            # Properly escape the path for shell commands
            import shlex
            escaped_path = shlex.quote(str_path)
            
            # Use SetFile command which is available on most macOS systems
            # The -d flag sets the creation date
            cmd = f"SetFile -d '{date_str}' {escaped_path}"
            result = os.system(cmd)
            
            if result != 0:
                print(f"Warning: SetFile command failed with code {result}")
                # Try alternative if available
                try:
                    # Format date for touch command (YYYYMMDDhhmm.ss)
                    touch_date = timestamp.strftime('%Y%m%d%H%M.%S')
                    os.system(f"touch -t {touch_date} {escaped_path}")
                except Exception as e:
                    print(f"Warning: Failed to set date using touch: {e}")
            
            return True
            
        except Exception as e:
            print(f"Warning: Failed to set creation time on macOS: {e}")
    
    else:  # Linux and others
        try:
            # Format date for touch command (YYYYMMDDhhmm.ss)
            touch_date = timestamp.strftime('%Y%m%d%H%M.%S')
            
            # Properly escape the path for shell commands
            import shlex
            escaped_path = shlex.quote(str_path)
            
            cmd = f"touch -t {touch_date} {escaped_path}"
            result = os.system(cmd)
            
            if result != 0:
                print(f"Warning: touch command failed with code {result}")
            
            return True
            
        except Exception as e:
            print(f"Warning: Failed to set creation time on Linux: {e}")
    
    # If we got here, the platform-specific attempt failed
    print(f"Warning: Could not set creation time on {system} platform")
    return False


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


def update_photo_timestamps(file_path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Update EXIF timestamps in the photo file based on its filename.
    Returns (success, message) tuple.
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)
        
    filename = file_path.name
    timestamp = extract_timestamp_from_filename(filename)
    
    if not timestamp:
        return False, f"Could not extract timestamp from filename: {filename}"
    
    # Format timestamp for EXIF
    exif_timestamp = format_exif_datetime(timestamp)
    
    if dry_run:
        return True, f"Would update timestamp for {filename} to {exif_timestamp}"
    
    exif_success = False
    exif_message = ""
    
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
        
        exif_success = True
        exif_message = f"Updated EXIF timestamp for {filename} to {exif_timestamp}"
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
            os.replace(temp_file, str(file_path))
            
            exif_success = True
            exif_message = f"Updated EXIF timestamp for {filename} (using PIL fallback)"
        except Exception as e2:
            exif_success = False
            exif_message = f"Error updating EXIF data: {e}; Fallback also failed: {e2}"
    
    # Always try to update file system timestamps, even if EXIF update failed
    fs_success = set_file_times(file_path, timestamp)
    
    if exif_success and fs_success:
        return True, f"Updated EXIF and file timestamps for {filename} to {exif_timestamp}"
    elif exif_success:
        return True, f"Updated EXIF timestamps but failed to set file creation time for {filename}"
    elif fs_success:
        return True, f"Updated file timestamps but failed to set EXIF data for {filename}: {exif_message}"
    else:
        return False, f"Failed to update both EXIF and file timestamps for {filename}: {exif_message}"


def process_directory(directory, recursive: bool = False, 
                     extensions: List[str] = None, dry_run: bool = False) -> Tuple[int, int]:
    """
    Process all images in a directory.
    Returns (success_count, failure_count) tuple.
    """
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.heic']
    
    success_count = 0
    failure_count = 0
    
    # Convert directory to Path object if it's a string
    if isinstance(directory, str):
        directory = Path(directory)
    
    # Get all files in directory
    try:
        if recursive:
            # Use rglob with a pattern that matches all files
            files = list(directory.rglob('*'))
        else:
            # Use iterdir to get immediate files only
            files = list(directory.iterdir())
            
        # Filter to keep only files (not directories)
        files = [f for f in files if f.is_file()]
    except Exception as e:
        print(f"Error accessing directory {directory}: {e}")
        return 0, 0
    
    # Filter by extensions
    image_files = [f for f in files if f.suffix.lower() in extensions]
    
    print(f"Found {len(image_files)} image files to process")
    
    for i, file_path in enumerate(image_files, 1):
        file_name = file_path.name
        print(f"Processing [{i}/{len(image_files)}] {file_name}...", end=" ")
        
        try:
            success, message = update_photo_timestamps(file_path, dry_run)
            print(message)
            
            if success:
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            print(f"Unexpected error processing {file_name}: {e}")
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
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed output for debugging')
    
    args = parser.parse_args()
    
    # Print system info for debugging
    system = platform.system()
    print(f"Running on: {system} ({platform.platform()})")
    print(f"Python version: {platform.python_version()}")
    print(f"Creation time support: {'Available' if HAS_CREATION_TIME else 'Not available'}")
    
    try:
        directory = Path(args.directory)
        if not directory.exists() or not directory.is_dir():
            print(f"Error: {args.directory} is not a valid directory")
            return 1
    except Exception as e:
        print(f"Error with path: {e}")
        return 1
    
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                 for ext in args.extensions.split(',')]
    
    print(f"{'DRY RUN - ' if args.dry_run else ''}Processing images in {directory}")
    print(f"File extensions: {', '.join(extensions)}")
    print(f"Recursive mode: {'Yes' if args.recursive else 'No'}")
    
    # Test creation time on a temp file if not in dry run mode
    if not args.dry_run and args.verbose:
        try:
            print("Testing creation time setting capability...")
            import tempfile
            test_file = Path(tempfile.mktemp(suffix='.txt'))
            with open(test_file, 'w') as f:
                f.write("Test file for timestamp setting")
            
            test_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
            if set_file_times(test_file, test_time):
                actual_time = datetime.datetime.fromtimestamp(os.path.getmtime(test_file))
                print(f"Test file modification time set to: {actual_time}")
                print(f"Target time was: {test_time}")
                print(f"Difference: {abs((actual_time - test_time).total_seconds())} seconds")
            else:
                print("Failed to set test file timestamp")
            
            # Test a path with spaces
            if system == 'Darwin' or system == 'Linux':
                test_space_file = Path(os.path.join(os.path.dirname(test_file), "test with spaces.txt"))
                with open(test_space_file, 'w') as f:
                    f.write("Test file with spaces for timestamp setting")
                
                # Try setting time on file with spaces in name
                space_result = set_file_times(test_space_file, test_time)
                print(f"Setting time on file with spaces: {'Success' if space_result else 'Failed'}")
                os.unlink(test_space_file)
            
            os.unlink(test_file)
        except Exception as e:
            print(f"Error during timestamp test: {e}")
    
    try:
        success, failure = process_directory(
            directory, 
            recursive=args.recursive,
            extensions=extensions,
            dry_run=args.dry_run
        )
        
        print(f"\nSummary: {success} succeeded, {failure} failed")
        return 0 if failure == 0 else 1
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())