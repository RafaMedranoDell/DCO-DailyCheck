# MISSION: Update Datastore Usage Thresholds (vCenter)

The objective was to adjust the visual alerts for datastore capacity in vCenter reports to align with new management thresholds:
- **Green (OK)**: < 85%
- **Yellow (Warning)**: 85% ≤ x < 95%
- **Red (Critical)**: ≥ 95%

## Implementation Details

### Centralized Logic Reuse
The implementation avoids explicit `if/elif` statements by utilizing the common library function `DCOreport.rate_num_value()`. This ensures that any change to the rating logic itself is handled in one place, while the vCenter-specific thresholds are passed as parameters.

### Modules Updated

#### 1. Analysis Logic (`src/VC/VCprocessinfo.py`)
The status shown in the **Daily Check (DC)** summary now uses the rating function to determine the aggregate health label.
```python
ds_status = DCOreport.rate_num_value(
    max_used, 
    rate_intervals=[0, 85, 95, 101], 
    rating=["OK", "Warning", "Critical"]
)
```

#### 2. Visual Styling (`src/VC/VCcreatereportDCI.py`)
The detailed table in the **Investigation (DCI)** report uses the same logic via a partial function to apply CSS colors.
```python
color_datastore_usage = functools.partial(
    DCOreport.rate_num_value,
    rate_intervals=[0, 85, 95, 101],
    rating=DCOreport.COLORS_GYR,
    force_conversion=True
)
```

## Impact and Benefits
- **No Side Effects**: The change is strictly confined to the `src/VC/` directory. No other system modules (ECS, DD, etc.) are affected.
- **Code Cleanliness**: Reduced complexity by removing manual boundary checks.
- **Improved Accuracy**: Using `[0, 85, 95, 101]` as intervals handles cases up to and including 100% capacity and provides a buffer for rounding errors.
