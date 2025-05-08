# Background

When copying media (photos and videos) from your PS5 to a USB drive, it sets the metadata create time to the current time instead of the original timestamp. However the timestamp is located in the filename, e.g. FINAL FANTASY XVI_20230622012416.jpg

# Implementation

## Prompt

Queried Claude (3.7 Sonnet) with this prompt:

> I want to have a script which will edit the timestamp of photos to match a timestamp present in the filename. I'd like a typescript or python implementation. 
> 
> The timestamp in the filename is this format: YYYYMMDDhhmm Example: 20201114205504


## Claude reponse:


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
