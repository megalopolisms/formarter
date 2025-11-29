# Analyze Docket

Analyze a federal litigation docket for deadlines, motion chains, and alerts.

## Instructions

When this command is invoked with a case number (e.g., `/analyze-docket 178`), do the following:

1. Read the docket data from `/Users/yuripetrinim5/Dropbox/Formarter Folder/dockets/index.json`
2. Filter entries for the specified case
3. Run the docket analyzer using Python:

```python
import sys
sys.path.insert(0, '/Users/yuripetrinim5/formarter')
from src.docket_analyzer import DocketAnalyzer

# Load entries for the case
entries = [...]  # Entries from index.json for this case

analyzer = DocketAnalyzer(is_pro_se=True)
results = analyzer.analyze_entries(entries)
print(analyzer.format_deadline_report())
```

4. Present the results showing:
   - OVERDUE deadlines (critical)
   - UPCOMING deadlines within 7 days
   - Motion status summary (pending vs resolved)
   - Motion chains (which responses/replies go with which motions)

## Pro Se Rule 6(d) Adjustments

As a pro se litigant, you get +3 days added to response deadlines when served electronically or by mail:
- Motion Response: 14 + 3 = 17 days
- Motion Reply: 7 + 3 = 10 days
- Answer: 21 + 3 = 24 days
- Discovery Response: 30 + 3 = 33 days

## Case Number: $ARGUMENTS
