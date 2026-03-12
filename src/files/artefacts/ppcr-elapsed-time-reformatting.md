# MISSION: Human-readable Elapsed Time in PPCR Report

The objective was to improve the "Protection Jobs" table in the PowerProtect Cyber Recovery (PPCR) report by converting the "Elapsed seconds" field into a human-readable format (`Dd HHh MMm`) and renaming the column to "Elapsed time".

## Changes Implemented

### src/common/functions.py
- Updated `format_duration(seconds)` to include zero padding: `f"{days}d {hours:02d}h {minutes:02d}m"`.

### src/PPCR/PPCRcreatereportDCI.py
- Refactored to load raw DataFrames and perform renaming/formatting **BEFORE** styling to avoid `KeyError`.

```python
        df_protection = dcocfg.load_csv_to_dataframe(system, instance, "protectionJobs")
        if not df_protection.empty:
            if "Elapsed seconds" in df_protection.columns:
                df_protection["Elapsed seconds"] = pd.to_numeric(df_protection["Elapsed seconds"]).apply(fn.format_duration)
                df_protection = df_protection.rename(columns={"Elapsed seconds": "Elapsed time"})

            protectionJobs = DCOreport.table_base_styler(df_protection)
            # ... apply remaining styles
```
