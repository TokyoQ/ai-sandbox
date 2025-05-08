# Background

When copying media (photos and videos) from your PS5 to a USB drive, it sets the metadata create time to the current time instead of the original timestamp. However the timestamp is located in the filename, e.g. FINAL FANTASY XVI_20230622012416.jpg

# Implementation

## Initial Prompt

Queried Claude (3.7 Sonnet) with this prompt:

> I want to have a script which will edit the timestamp of photos to match a timestamp present in the filename. I'd like a typescript or python implementation. 
> 
> The timestamp in the filename is this format: YYYYMMDDhhmm Example: 20201114205504


### Claude reponse:


I can create a script to modify photo timestamps based on the filename format you provided. Let's implement this in Python since it has great libraries for file manipulation and metadata handling.

I've created two implementations of a script that will modify photo timestamps based on the format you specified (YYYYMMDDhhmm):

Python Implementation:

Uses the piexif and Pillow libraries to modify EXIF metadata
Updates both the EXIF timestamps and the file modification time
Handles various image formats including JPG, PNG, TIFF, and HEIC
Supports recursive directory processing


TypeScript Implementation:

Uses exiftool-vendored to handle image metadata
Updates all date/time fields in the EXIF data as well as file modification times
Includes similar features: recursive processing, dry-run mode, and custom extension filtering



Both scripts:

Extract timestamps from filenames with format YYYYMMDDhhmm(ss)
Support dry-run mode to preview changes without modifying files
Provide detailed reporting of processed files
Include error handling for invalid files or timestamps

Usage Example (Python)
```
# Install dependencies
pip install piexif Pillow

# Basic usage
python photo_timestamp_updater.py /path/to/photos

# Process recursively with dry run
python photo_timestamp_updater.py /path/to/photos -r -d

# Specify file extensions
python photo_timestamp_updater.py /path/to/photos -e .jpg,.png
```

Usage Example (TypeScript)
```
bash# Install dependencies
npm install exiftool-vendored fs-extra glob yargs

# Compile TypeScript
tsc photo_timestamp_updater.ts

# Basic usage
node photo_timestamp_updater.js /path/to/photos

# Process recursively with dry run
node photo_timestamp_updater.js /path/to/photos -r --dry-run
```

Would you like me to explain any specific part of either implementation in more detail?


## Second update

Prompt:

> I am trying it out but getting this error: "Error updating EXIF data for"
> My full output:
> 
> Processing images in /Volumes/Q DRIVE/PS5/CREATE/Screenshots/A KING'S TALE_ FINAL FANTASY XV
> File extensions: .jpg, .jpeg, .png, .tiff, .tif, .heic
> Recursive mode: No
> Found 2 image files to process
> Processing [1/2] A KING'S TALE_ FINAL FANTASY XV_20201114205504.jpg... Error updating EXIF data for A KING'S TALE_ FINAL FANTASY XV_20201114205504.jpg: 306
> Processing [2/2] A KING'S TALE_ FINAL FANTASY XV_20201114205239.jpg... Error updating EXIF data for A KING'S TALE_ FINAL FANTASY XV_20201114205239.jpg: 306
> 
> Summary: 0 succeeded, 2 failed

### Response

The error code "306" suggests an issue with the EXIF data manipulation. Let's fix the Python script to better handle this specific problem, which is likely related to how the EXIF data is being saved or processed.

I've updated the Python script to fix the error you're encountering. The error code 306 typically happens with issues in EXIF data manipulation, especially when dealing with files that have paths or names with special characters (like apostrophes in "A KING'S TALE").

Key Improvements in the Updated Script:

Added a two-tier approach to updating EXIF data:

First tries using piexif directly on the file
Falls back to using PIL/Pillow with a temporary file approach if the direct method fails


Improved error handling that provides more detailed error messages
Added a note about handling paths with spaces in the script documentation

How to Run the Script with Your Path:
Since you're on macOS (I can tell from your path /Volumes/Q DRIVE/...), make sure to use quotes around your path:

```
python photo_timestamp_updater.py "/Volumes/Q DRIVE/PS5/CREATE/Screenshots/A KING'S TALE_ FINAL FANTASY XV"
```

If you're still having issues, you might try the fallback approach of using exiftool directly which is generally more robust for EXIF manipulation. Here's a simple one-liner that would work with exiftool (if you have it installed):

```
exiftool "-DateTimeOriginal<${filename:11:8} ${filename:19:2}:${filename:21:2}:${filename:23:2}" "-CreateDate<${filename:11:8} ${filename:19:2}:${filename:21:2}:${filename:23:2}" "-ModifyDate<${filename:11:8} ${filename:19:2}:${filename:21:2}:${filename:23:2}" "/Volumes/Q DRIVE/PS5/CREATE/Screenshots/A KING'S TALE_ FINAL FANTASY XV"
```

But try the updated Python script first - it should handle your case better now.
