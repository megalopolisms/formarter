# Quick Start Guide - Case Renaming Script

## Overview

This script renames all PDF and TXT files in your case library to proper Bluebook citation format.

## Step 1: Preview Changes (DRY RUN)

**IMPORTANT: Always run this first to see what will change!**

```bash
cd /Users/yuripetrinim5/formarter
python3 src/utils/rename_cases.py
```

This will show you:
- Exactly what files will be renamed
- What the new names will be
- Any errors or issues that might occur

**No files are changed in dry-run mode!**

## Step 2: Review the Preview

Look through the output carefully:
- Check that case names are formatted correctly
- Verify reporter abbreviations are correct
- Make sure years and page numbers are accurate
- Note any "SKIPPED" or "ERROR" messages

## Step 3: Run the Actual Rename

Once you're satisfied with the preview:

```bash
python3 src/utils/rename_cases.py --live
```

This will:
1. Rename all PDF files
2. Rename all TXT files
3. Create a backup: `index.json.backup`
4. Update `index.json` with new filenames

## Step 4: Verify Results

After running, check:
- The summary statistics at the end
- Open a few renamed files to make sure they work
- Check `index.json` to see updated filenames

## What if Something Goes Wrong?

The script creates a backup before making changes. To restore:

```bash
cp ~/Dropbox/Formarter\ Folder/case_library/index.json.backup \
   ~/Dropbox/Formarter\ Folder/case_library/index.json
```

Then manually rename any files that were changed (the dry-run output will help you identify them).

## Command Line Options

### Quiet Mode
Only show summary (less verbose):
```bash
python3 src/utils/rename_cases.py --live --quiet
```

### Custom Case Library Path
Use a different case library directory:
```bash
python3 src/utils/rename_cases.py --case-library /path/to/case_library/
```

### Help
See all options:
```bash
python3 src/utils/rename_cases.py --help
```

## Example Transformations

| Before | After |
|--------|-------|
| `JOHNSON v JONES 115 SCt 2151.pdf` | `Johnson v. Jones, 115 S. Ct. 2151 (1995).pdf` |
| `KEKO v HINGLE 318 F3d 639.pdf` | `Keko v. Hingle, 318 F.3d 639 (5th Cir. 2002).pdf` |
| `miranda_v_arizona_384_us_436_1966.pdf` | `Miranda v. Arizona, 384 U.S. 436 (1966).pdf` |
| `O'SHEA v LITTLETON 94 SCt 669.pdf` | `O'Shea v. Littleton, 94 S. Ct. 669 (1974).pdf` |

## Troubleshooting

### "Insufficient data" messages
Some cases in your index.json are missing required fields (case_name, volume, reporter, page, or year). These will be skipped.

### "Target file already exists" errors
Two different cases would rename to the same filename. You'll need to manually resolve these conflicts.

### "File not found" warnings
The PDF or TXT file listed in index.json doesn't exist in the case_library directory. The index might be out of sync with actual files.

## Need More Details?

See the full documentation in `README.md` in the same directory.
