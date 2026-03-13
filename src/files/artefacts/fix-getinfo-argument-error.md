# MISSION: Fix getinfo Argument Error

The objective was to fix a crash when running the `getinfo` phase, caused by `DCO-DailyCheck.py` passing an unexpected `hours_ago` parameter to the `getinfo` functions of certain modules.

## Analysis
The main script `DCO-DailyCheck.py` passes `hours_ago` to all system `getinfo` calls. While the vCenter (`VC`) module was already updated to handle extra arguments, the `PPCR` and `DD` modules were not, leading to a `TypeError: getinfo() got an unexpected keyword argument 'hours_ago'`.

## Changes Implemented

### 1. PPCR Module (`src/PPCR/PPCRgetinfo.py`)
Updated the function signature to accept `**kwargs`. This makes the function robust against extra arguments and allows the use of `hours_ago` inside the logic if needed in the future.
```python
def getinfo(dcocfg, **kwargs):
    # Example usage:
    # hours = kwargs.get('hours_ago', 24)
```

### 2. DD Module (`src/DD/DDgetinfo.py`)
Updated the function signature to accept `**kwargs` for consistency and to prevent future crashes in Data Domain systems.
```python
def getinfo(dcocfg, **kwargs):
```

## Branch
`fix/ppcr-getinfo-argument-error`

## Result
The script now runs the `getinfo` phase for PPCR and DD systems without crashing. The modules are now "future-proofed" as they will safely ignore or utilize any new parameters passed by the core script.
