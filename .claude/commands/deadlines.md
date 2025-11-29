# Show All Deadlines

Show all pending deadlines across all federal cases with Rule 6(d) pro se adjustments.

## Instructions

1. Load docket data from `/Users/yuripetrinim5/Dropbox/Formarter Folder/dockets/index.json`
2. Run the analyzer on each case (178, 233, 254)
3. Consolidate all alerts and sort by urgency
4. Display overdue items first, then upcoming deadlines

## Deadline Rules (Pro Se with Rule 6(d) +3 days)

| Type | Base | Pro Se Total |
|------|------|--------------|
| Motion Response | 14 | 17 days |
| Motion Reply | 7 | 10 days |
| Answer | 21 | 24 days |
| Discovery Response | 30 | 33 days |
| Appeal | 30 | 33 days |
| Magistrate Objection | 14 | 17 days |

## Jurisdictional (NO adjustment)
- Rule 59 Motion: 28 days (strict)
- Rule 60 Motion: 1 year (strict)
- Service of Complaint: 90 days (strict)

Run Python analysis and format results clearly with case numbers.
