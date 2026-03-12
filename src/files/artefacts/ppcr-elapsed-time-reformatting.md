# MISSION: Human-readable Elapsed Time in PPCR Report

The objective was to improve the "Protection Jobs" table in the PowerProtect Cyber Recovery (PPCR) report by converting the "Elapsed seconds" field into a human-readable format (`Dd HHh MMm`) and renaming the column to "Elapsed time".

## Changes Implemented

### 1. Centralized Time Formatting (`src/common/functions.py`)
Updated the `format_duration(seconds)` function to include zero padding for hours and minutes.
- **Format**: `f"{days}d {hours:02d}h {minutes:02d}m"`
- **Improvement**: Ensures visual alignment in tables (e.g., `04h 09m` instead of `4h 9m`).

### 2. Report Generation Fix (`src/PPCR/PPCRcreatereportDCI.py`)
A `KeyError` was identified when renaming columns directly on a `Styler` object. To resolve this, the processing logic was refactored:
- **Raw Processing**: Structural changes (formatting and renaming) are now performed on the raw pandas DataFrame **before** initializing the Styler.
- **Dynamic Re-formatting**: Added a step in the report phase to re-apply the duration format. This ensures that even if the source CSV lacks padding (due to an old preprocess run), the final HTML report always displays the consistent `HHh MMm` format.

```python
        df_protection = dcocfg.load_csv_to_dataframe(system, instance, "protectionJobs")
        if not df_protection.empty:
            if "Elapsed seconds" in df_protection.columns:
                # Format and rename on raw DF
                df_protection["Elapsed seconds"] = pd.to_numeric(df_protection["Elapsed seconds"]).apply(fn.format_duration)
                df_protection = df_protection.rename(columns={"Elapsed seconds": "Elapsed time"})

            # Style only after structure is final
            protectionJobs = DCOreport.table_base_styler(df_protection)
```

## Verification
- Verified consistent alignment in "Policies", "System Jobs", and "Protection Jobs" tables.
- Confirmed that structural changes before styling prevent `KeyError` during HTML rendering.
