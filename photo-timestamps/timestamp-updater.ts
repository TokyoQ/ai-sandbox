#!/usr/bin/env node

/**
 * Photo Timestamp Updater
 * 
 * Updates photo timestamps based on date information in the filename.
 * Format expected: YYYYMMDDhhmm or YYYYMMDDhhmmss
 * 
 * Prerequisites:
 * - Node.js 16+
 * - npm install exiftool-vendored fs-extra glob yargs
 */

import { exiftool } from 'exiftool-vendored';
import * as fs from 'fs-extra';
import * as path from 'path';
import * as glob from 'glob';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

interface ProcessOptions {
  recursive: boolean;
  dryRun: boolean;
  extensions: string[];
}

// Extract timestamp from filename using regex
function extractTimestampFromFilename(filename: string): Date | null {
  // Match YYYYMMDD followed by hhmmss (with optional seconds)
  const match = filename.match(/(\d{8})(\d{4})(\d{2})?/);
  if (!match) return null;

  const datePart = match[1];
  const timePart = match[2];
  const secondsPart = match[3] || '00'; // Default to 00 seconds if not provided

  try {
    const year = parseInt(datePart.substring(0, 4));
    const month = parseInt(datePart.substring(4, 6));
    const day = parseInt(datePart.substring(6, 8));
    const hour = parseInt(timePart.substring(0, 2));
    const minute = parseInt(timePart.substring(2, 4));
    const second = parseInt(secondsPart);

    return new Date(year, month - 1, day, hour, minute, second);
  } catch (error) {
    return null;
  }
}

// Format date to EXIF format (YYYY:MM:DD HH:MM:SS)
function formatExifDate(date: Date): string {
  return date.toISOString()
    .replace(/T/, ' ')         // Replace T with space
    .replace(/\.\d+Z$/, '')    // Remove milliseconds and Z
    .replace(/-/g, ':');       // Replace hyphens with colons in date part
}

// Process a single image file
async function processImage(
  filePath: string, 
  dryRun: boolean
): Promise<{ success: boolean; message: string }> {
  const filename = path.basename(filePath);
  const timestamp = extractTimestampFromFilename(filename);

  if (!timestamp) {
    return { 
      success: false, 
      message: `Could not extract timestamp from filename: ${filename}` 
    };
  }

  try {
    // Format timestamp for EXIF
    const exifTimestamp = formatExifDate(timestamp);
    
    if (dryRun) {
      return { 
        success: true, 
        message: `Would update timestamp for ${filename} to ${exifTimestamp}` 
      };
    }
    
    // Update EXIF metadata
    await exiftool.write(filePath, {
      AllDates: exifTimestamp,  // Updates all date/time fields at once
    });
    
    // Update file modification time
    await fs.utimes(filePath, timestamp, timestamp);
    
    return { 
      success: true, 
      message: `Updated timestamp for ${filename} to ${exifTimestamp}` 
    };
  } catch (error) {
    return { 
      success: false, 
      message: `Error updating metadata for ${filename}: ${error instanceof Error ? error.message : String(error)}` 
    };
  }
}

// Process all images in a directory
async function processDirectory(
  directory: string, 
  options: ProcessOptions
): Promise<{ success: number; failure: number }> {
  const { recursive, dryRun, extensions } = options;
  
  // Create the glob pattern
  const pattern = recursive 
    ? `${directory}/**/*.{${extensions.join(',')}}` 
    : `${directory}/*.{${extensions.join(',')}}`;
  
  let imageFiles: string[] = [];
  try {
    imageFiles = glob.sync(pattern, { nocase: true });
  } catch (error) {
    console.error('Error finding files:', error instanceof Error ? error.message : String(error));
    return { success: 0, failure: 0 };
  }
  
  console.log(`Found ${imageFiles.length} image files to process`);
  
  let successCount = 0;
  let failureCount = 0;
  
  for (let i = 0; i < imageFiles.length; i++) {
    const filePath = imageFiles[i];
    process.stdout.write(`Processing [${i + 1}/${imageFiles.length}] ${path.basename(filePath)}... `);
    
    const { success, message } = await processImage(filePath, dryRun);
    console.log(message);
    
    if (success) {
      successCount++;
    } else {
      failureCount++;
    }
  }
  
  return { success: successCount, failure: failureCount };
}

async function main() {
  const argv = yargs(hideBin(process.argv))
    .option('recursive', {
      alias: 'r',
      type: 'boolean',
      description: 'Recursively process subdirectories',
      default: false
    })
    .option('dry-run', {
      alias: 'd',
      type: 'boolean',
      description: 'Perform a dry run without modifying files',
      default: false
    })
    .option('extensions', {
      alias: 'e',
      type: 'string',
      description: 'Comma-separated list of file extensions to process',
      default: 'jpg,jpeg,png,tiff,tif,heic'
    })
    .positional('directory', {
      type: 'string',
      demandOption: true,
      describe: 'Directory containing image files'
    })
    .demandCommand(1, 'You must provide a directory path')
    .help()
    .argv as any;
  
  const directory = argv._[0];
  const extensions = argv.extensions.split(',').map((ext: string) => ext.trim().toLowerCase());
  
  try {
    const dirStats = await fs.stat(directory);
    if (!dirStats.isDirectory()) {
      console.error(`Error: ${directory} is not a directory`);
      process.exit(1);
    }
  } catch (error) {
    console.error(`Error: ${directory} does not exist or is not accessible`);
    process.exit(1);
  }
  
  console.log(`${argv.dryRun ? 'DRY RUN - ' : ''}Processing images in ${directory}`);
  console.log(`File extensions: ${extensions.join(', ')}`);
  console.log(`Recursive mode: ${argv.recursive ? 'Yes' : 'No'}`);
  
  try {
    const { success, failure } = await processDirectory(directory, {
      recursive: argv.recursive,
      dryRun: argv.dryRun,
      extensions
    });
    
    console.log(`\nSummary: ${success} succeeded, ${failure} failed`);
    
    // Clean up and exit
    await exiftool.end();
    process.exit(failure === 0 ? 0 : 1);
  } catch (error) {
    console.error('Error:', error instanceof Error ? error.message : String(error));
    await exiftool.end();
    process.exit(1);
  }
}

main().catch(console.error);