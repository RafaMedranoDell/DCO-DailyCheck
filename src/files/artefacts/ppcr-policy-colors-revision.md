# MISSION: Refine PPCR Policy Table Coloring

The goal was to provide a clearer visual distinction in the "Policies" table between policies that are simply outdated (>24h since last update) and those that are in an irregular state (missing update date due to unfinished jobs).

## Logic Implemented
The `colorByPolicyDuration` function in `src/PPCR/PPCRcreatereportDCI.py` was updated to handle three distinct states:

| Condition | State | Color | Styler Variable |
| :--- | :--- | :--- | :--- |
| `Update date` is `"-"` | Pending / Unfinished | **Yellow** | `PASTEL_YELLOW` |
| Age >= 24 hours | Outdated / Critical | **Red** | `PASTEL_RED` |
| Age < 24 hours | Updated / OK | **Green** | `PASTEL_GREEN` |

## Changes in src/PPCR/PPCRcreatereportDCI.py

### Refined Coloring Function
```python
def colorByPolicyDuration(row):
    if row["Update date"] == "-":
        color = DCOreport.PASTEL_YELLOW
    elif row["elapsed_seconds"] >= 3600*24:
        color = DCOreport.PASTEL_RED
    else:
        color = DCOreport.PASTEL_GREEN
    return [color] * len(row)
```

### Table Processing Enhancement
The loading of the "Policies" table was also updated to use the same "Raw-First" processing pattern established in the previous fix. This ensures consistent time formatting (`00h 00m`) even if the preprocessing CSV was generated with an older version of the code.

## Verification
- **SAP** (Unfinished jobs): Now shows in **Yellow** (Check jobs).
- **Outdated Policies** (e.g., 4 days old): Now show in **Red**.
- **Recent Policies**: Continue to show in **Green**.
