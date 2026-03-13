# PROPOSED PLAN: Enforce Fixed Order in Reports

The goal is to ensure that the systems in the final HTML reports (DC and DCI) always follow a specific logical order, regardless of how they are defined in the configuration file.

## Requested Hierarchy & Order
1.  **Protection**
    *   Power Protect Cyber Recovery (PPCR)
    *   Power Protect Data Manager (PPDM)
    *   Data Domain (DD)
2.  **Storage**
    *   ECS
3.  **Compute**
    *   vSphere (VC)
    *   Servers (iDRAC)
4.  **Network**
    *   Switches (OS10)

## Implementation Details

### 1. Centralized Priority (`src/common/DCOconfig.py`)
The `systems()` method in `DCOconfig.py` has been updated to return the system keys sorted by a predefined priority list. This ensures every phase (getinfo, process, report) follows the same logical flow.

```python
SYSTEM_PRIORITY = ["PPCR", "PPDM", "DD", "ECS", "VC", "IDRAC", "OS10"]
```

### 2. Universal Order (DC & DCI)
Both the Daily Check (DC) and Investigation (DCI) reports use the `systems()` method to iterate through products. By ordering the systems at the configuration level:
-   **reportDC**: Shows Protection (PPCR, PPDM, DD), Storage (ECS), Compute (VC, IDRAC), Network (OS10).
-   **reportDCI**: Shows detailed tables in the same consistent sequence.

## Verification
The sorting logic was tested with various configurations, confirming that PPCR always precedes DD, and categorical groupings are respected across the report.
