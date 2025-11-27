# Case Renaming Checklist

Use this checklist when running the case renaming script to ensure everything goes smoothly.

## Pre-Flight Checks

- [ ] Backup your case library directory (entire folder, just in case)
- [ ] Close any applications that might have case files open
- [ ] Verify you're in the correct directory: `/Users/yuripetrinim5/formarter`

## Step 1: Preview Run

- [ ] Run the dry-run command:
  ```bash
  python3 src/utils/rename_cases.py
  ```

- [ ] Review the output and verify:
  - [ ] Case names are properly capitalized
  - [ ] Reporter abbreviations look correct (F.3d, U.S., S. Ct., etc.)
  - [ ] Years and page numbers are accurate
  - [ ] No concerning "ERROR" messages

- [ ] Check the summary statistics:
  - [ ] Total cases matches expectations
  - [ ] Number of renames seems reasonable
  - [ ] Insufficient data count is acceptable
  - [ ] Error count is zero or explainable

## Step 2: Address Any Issues

If you see problems in the preview:

- [ ] Review cases with "Insufficient data" - do they need to be manually fixed in index.json?
- [ ] Check any "ERROR" messages - are there file conflicts?
- [ ] Verify unusual case names (with apostrophes, hyphens, etc.) are handled correctly

## Step 3: Execute Rename

- [ ] Run the live rename command:
  ```bash
  python3 src/utils/rename_cases.py --live
  ```

- [ ] Watch for any errors during execution
- [ ] Verify the backup was created: `index.json.backup`

## Step 4: Post-Rename Verification

- [ ] Check the summary statistics again
- [ ] Spot-check 5-10 renamed files:
  - [ ] PDFs open correctly
  - [ ] Filenames match Bluebook format
  - [ ] TXT files exist alongside PDFs

- [ ] Verify index.json was updated:
  ```bash
  python3 -c "import json; data=json.load(open('/Users/yuripetrinim5/Dropbox/Formarter Folder/case_library/index.json')); print(f'Sample: {data[\"cases\"][0][\"pdf_filename\"]}')"
  ```

- [ ] Test your application to make sure it still works with renamed files

## If Something Went Wrong

- [ ] Don't panic! You have a backup.
- [ ] Restore index.json from backup:
  ```bash
  cp ~/Dropbox/Formarter\ Folder/case_library/index.json.backup \
     ~/Dropbox/Formarter\ Folder/case_library/index.json
  ```
- [ ] Review the error messages
- [ ] Fix the issues and try again

## Success Criteria

- ✓ All files renamed successfully
- ✓ index.json updated with new filenames
- ✓ Backup created
- ✓ Application still functions correctly
- ✓ Files follow consistent Bluebook format

## Statistics to Record

After successful renaming, record these for reference:

- Total cases: ___________
- Files renamed: ___________
- Already correct: ___________
- Skipped: ___________
- Errors: ___________
- Date completed: ___________

## Notes

Use this space to record any issues, special cases, or observations:

---
