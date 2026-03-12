# MISSION: Human-readable Elapsed Time in PPCR Report

The objective was to improve the "Protection Jobs" table in the PowerProtect Cyber Recovery (PPCR) report by converting the "Elapsed seconds" field into a human-readable format (`Dd HHh MMm`) and renaming the column to "Elapsed time".

## Changes Implemented

### src/PPCR/PPCRcreatereportDCI.py
1.  **Helper Function**: Added `format_elapsed_time(seconds)`.
2.  **Table Processing**: Updated "System Jobs" and "Protection Jobs" table generation.

```diff
--- a/src/PPCR/PPCRcreatereportDCI.py
+++ b/src/PPCR/PPCRcreatereportDCI.py
@@ -1,5 +1,6 @@
 import functools
 import pandas as pd
+import common.functions as fn
 from common.DCOconfig import DCOconfig
 import common.DCOreport as DCOreport
 
@@ -6,3 +6,22 @@
+def format_elapsed_time(seconds):
+    """
+    Formats seconds into 'Dd HHh MMm' with zero padding for hours and minutes.
+    """
+    try:
+        # Check if the value is empty or N/A
+        if not seconds or str(seconds).lower() == 'n/a':
+            return seconds
+        
+        seconds = float(seconds)
+        total_minutes = int(seconds // 60)
+        days = total_minutes // (24 * 60)
+        hours = (total_minutes % (24 * 60)) // 60
+        minutes = total_minutes % 60
+        return f"{days}d {hours:02d}h {minutes:02d}m"
+    except (ValueError, TypeError):
+        return seconds
+
+
 
 def colorAlertsBySeverityVal(val):
@@ -53,6 +72,11 @@
 
         systemJobs = DCOreport.csv_to_styleddf(system, instance, "systemJobs", dcocfg)
         if not systemJobs.data.empty:
+            # Reformat 'Elapsed seconds' as requested
+            if "Elapsed seconds" in systemJobs.data.columns:
+                systemJobs.data["Elapsed seconds"] = systemJobs.data["Elapsed seconds"].apply(format_elapsed_time)
+                systemJobs.data = systemJobs.data.rename(columns={"Elapsed seconds": "Elapsed time"})
+            
             systemJobs = DCOreport.column_wordwrap(systemJobs, columns=['Detailed description'])
             systemJobs = systemJobs.apply(color_jobsByStatus, axis=1)
             dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "System Jobs", systemJobs, tableset="ts4")
@@ -59,5 +83,10 @@
         protectionJobs = DCOreport.csv_to_styleddf(system, instance, "protectionJobs", dcocfg)
         if not protectionJobs.data.empty:
+            # Reformat 'Elapsed seconds' as requested
+            if "Elapsed seconds" in protectionJobs.data.columns:
+                protectionJobs.data["Elapsed seconds"] = protectionJobs.data["Elapsed seconds"].apply(format_elapsed_time)
+                protectionJobs.data = protectionJobs.data.rename(columns={"Elapsed seconds": "Elapsed time"})
+
             protectionJobs = DCOreport.column_wordwrap(protectionJobs, columns=['Detailed description'])
             protectionJobs = protectionJobs.apply(color_jobsByStatus, axis=1)
             dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "Protection Jobs", protectionJobs, tableset="ts5")
```
