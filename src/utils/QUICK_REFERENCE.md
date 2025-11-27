# Quick Reference Card

## Commands

### Preview Changes (DRY RUN - Safe!)
```bash
python3 src/utils/rename_cases.py
```

### Actually Rename Files (LIVE MODE)
```bash
python3 src/utils/rename_cases.py --live
```

### Quiet Mode (Less Output)
```bash
python3 src/utils/rename_cases.py --live --quiet
```

### Show Test Examples
```bash
python3 src/utils/test_rename.py
```

### Get Help
```bash
python3 src/utils/rename_cases.py --help
```

## File Locations

- **Script**: `/Users/yuripetrinim5/formarter/src/utils/rename_cases.py`
- **Case Library**: `~/Dropbox/Formarter Folder/case_library/`
- **Index**: `~/Dropbox/Formarter Folder/case_library/index.json`
- **Backup**: `~/Dropbox/Formarter Folder/case_library/index.json.backup`

## Format Examples

| Before | After |
|--------|-------|
| `JOHNSON v JONES 115 SCt 2151.pdf` | `Johnson v. Jones, 115 S. Ct. 2151 (1995).pdf` |
| `KEKO v HINGLE 318 F3d 639.pdf` | `Keko v. Hingle, 318 F.3d 639 (5th Cir. 2002).pdf` |
| `O'SHEA v LITTLETON 94 SCt 669.pdf` | `O'Shea v. Littleton, 94 S. Ct. 669 (1974).pdf` |

## Reporter Normalizations

| Input | Output |
|-------|--------|
| F3d | F.3d |
| F2d | F.2d |
| US | U.S. |
| SCt | S. Ct. |
| FSupp2d | F. Supp. 2d |
| FSupp3d | F. Supp. 3d |

## Safety Reminders

1. Always run dry-run first
2. Review the output carefully
3. Backup is created automatically
4. Script skips files with insufficient data
5. Won't overwrite existing files

## Recovery

If something goes wrong:
```bash
cp ~/Dropbox/Formarter\ Folder/case_library/index.json.backup \
   ~/Dropbox/Formarter\ Folder/case_library/index.json
```

## Documentation

- **Full Docs**: `src/utils/README.md`
- **Usage Guide**: `src/utils/USAGE.md`
- **Checklist**: `src/utils/CHECKLIST.md`
- **Summary**: `CASE_RENAME_SUMMARY.md`
