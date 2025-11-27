# Case Library Utilities

## rename_cases.py

Renames all case PDF and TXT files in the case library to a consistent Bluebook citation format.

### Target Format

```
Party v. Party, Volume Reporter Page (Year).pdf
```

**Examples:**
- `Miranda v. Arizona, 384 U.S. 436 (1966).pdf`
- `Keko v. Hingle, 318 F.3d 639 (5th Cir. 2002).pdf`
- `Smith v. Jones, 123 F. Supp. 2d 456 (2020).pdf`

### Features

- **Dry-run mode by default** - Shows what would be renamed without making changes
- **Reporter normalization** - Converts `F3d` to `F.3d`, `US` to `U.S.`, `SCt` to `S. Ct.`, etc.
- **Case name normalization** - Proper title case and `v.` separator
- **Safe filename handling** - Removes/replaces invalid characters
- **Index update** - Automatically updates `index.json` with new filenames
- **Backup creation** - Creates `index.json.backup` before modifying the index
- **Error handling** - Detects and reports file conflicts and missing data

### Usage

#### Dry Run (See What Would Change)

```bash
python src/utils/rename_cases.py
```

This is the default mode. It will show you all the renames that would happen without actually changing any files.

#### Live Mode (Actually Rename Files)

```bash
python src/utils/rename_cases.py --live
```

This will:
1. Rename all PDF and TXT files to Bluebook format
2. Create a backup of `index.json` as `index.json.backup`
3. Update `index.json` with the new filenames

#### Quiet Mode (Only Show Summary)

```bash
python src/utils/rename_cases.py --live --quiet
```

Shows only the summary statistics without detailed progress.

#### Custom Case Library Path

```bash
python src/utils/rename_cases.py --case-library /path/to/case_library/
```

### Reporter Normalizations

The script automatically normalizes reporter abbreviations:

| Input | Output |
|-------|--------|
| `F3d` | `F.3d` |
| `F2d` | `F.2d` |
| `US` | `U.S.` |
| `SCt` | `S. Ct.` |
| `FSupp2d` | `F. Supp. 2d` |
| `FSupp3d` | `F. Supp. 3d` |

### Case Name Normalizations

- Title case for party names
- Proper `v.` separator (not `V.`, `v`, or `vs`)
- Lowercase for articles and prepositions (of, the, in, at, by, for, on, and, or)
- Removes embedded citation info from case names

### What Gets Skipped

The script will skip cases that:
- Are already in the correct Bluebook format
- Have missing required data (case_name, volume, reporter, page, or year)
- Have file conflicts (when the target filename already exists)

### Error Handling

If errors occur, the script will:
- Report each error with details
- Continue processing other cases
- Exit with a non-zero code if any errors occurred
- NOT update the index if any renames failed

### Output Examples

**Dry Run Output:**
```
================================================================================
DRY RUN MODE - NO FILES WILL BE CHANGED
================================================================================

[1/142] Processing case ID: 2efbe726-0564-411e-a76f-64b6531a6815
  Current name: JOHNSON v. JONES
  New name: Johnson v. Jones, 115 S. Ct. 2151 (1995).pdf
  📄 Would rename PDF: JOHNSON v JONES 115 SCt 2151.pdf → Johnson v. Jones, 115 S. Ct. 2151 (1995).pdf
  📝 Would rename TXT: JOHNSON v JONES 115 SCt 2151.txt → Johnson v. Jones, 115 S. Ct. 2151 (1995).txt
```

**Summary Output:**
```
================================================================================
SUMMARY
================================================================================
Total cases: 142
Renamed: 135
Already correct: 5
Insufficient data: 2
Errors: 0
================================================================================
```

### Safety Features

1. **Dry-run by default** - Must explicitly use `--live` to rename files
2. **Backup creation** - Original `index.json` saved as `index.json.backup`
3. **Conflict detection** - Won't overwrite existing files
4. **Case-insensitive file search** - Handles filesystems with different case sensitivity
5. **Validation** - Checks for required data before renaming

### Recommended Workflow

1. First, run in dry-run mode to see what would change:
   ```bash
   python src/utils/rename_cases.py
   ```

2. Review the output carefully

3. If everything looks good, run in live mode:
   ```bash
   python src/utils/rename_cases.py --live
   ```

4. Check the results and verify `index.json` was updated correctly

5. If something went wrong, restore from backup:
   ```bash
   cp ~/Dropbox/Formarter\ Folder/case_library/index.json.backup \
      ~/Dropbox/Formarter\ Folder/case_library/index.json
   ```
