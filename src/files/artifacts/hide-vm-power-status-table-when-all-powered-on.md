# MISSION: Implement conditional and filtered display for VM Power Status table

The objective was modified to:
1. Hide the "VM Power Status Detail" table if all VMs are `POWERED_ON`.
2. If shown, the table must **only** include the VMs that are not in `POWERED_ON` state.

## Analysis Summary
- The script now filters the DataFrame loaded from `vmStatus.csv` before converting it to a Styled object.
- It uses `DCOreport.table_base_styler` directly on the filtered results to ensure project design standards (colors, headers, alignment) are maintained for the subset.

## Branch
`feature/hide-vm-power-status-table-when-all-powered-on`

## Changes Implemented

```diff
--- a/src/VC/VCcreatereportDCI.py
+++ b/src/VC/VCcreatereportDCI.py
@@ -56,13 +56,20 @@
-        vm_detail = DCOreport.csv_to_styleddf(system, instance, "vmStatus", dcocfg)
-        if not vm_detail.data.empty:
-            # Apply color to rows where VM is not POWERED_ON
-            vm_detail = vm_detail.apply(color_vm_state, axis=1)
-            
-            # Column word wrap for VM names if they are long
-            vm_detail = DCOreport.column_wordwrap(vm_detail, ["name"])
-            
-            dcorpt.add_table("Compute", "vSphere", instance, "VM Power Status Detail", vm_detail, tableset="Overview")
+        # Load raw dataframe first to filter
+        df_vms = dcocfg.load_csv_to_dataframe(system, instance, "vmStatus")
+        if not df_vms.empty:
+            # Filter to keep only VMs that are NOT POWERED_ON
+            df_off_vms = df_vms[df_vms["power_state"] != "POWERED_ON"]
+            
+            if not df_off_vms.empty:
+                # Create styled dataframe from the filtered results
+                vm_detail = DCOreport.table_base_styler(df_off_vms)
+                
+                # Apply color to rows (they will all be colored as they are not POWERED_ON)
+                vm_detail = vm_detail.apply(color_vm_state, axis=1)
+                
+                # Column word wrap for VM names if they are long
+                vm_detail = DCOreport.column_wordwrap(vm_detail, ["name"])
+                
+                dcorpt.add_table("Compute", "vSphere", instance, "VM Power Status Detail", vm_detail, tableset="Overview")
```

## Verification Results

Verified with updated test scenarios:

| Scenario | Expected Behavior | Result |
| :--- | :--- | :--- |
| **All VMs POWERED_ON** | Table "VM Power Status Detail" is hidden. | **SUCCESS** |
| **Mixed Status (2 ON, 2 OFF)** | Table shown with **only the 2 OFF VMs**. | **SUCCESS** |
| **No VMs (Empty File)** | Table is hidden. | **SUCCESS** |

### Verified HTML Content
In the "Mixed Status" test, the generated HTML table contained exactly 2 data rows, and none of them contained the text "POWERED_ON". All visible rows were correctly styled with `PASTEL_RED`.
