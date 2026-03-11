import pandas as pd
import common.DCOreport as DCOreport

# Global variable for the system type
system = "VC"

def color_datastore_usage(val):
    """
    Colors datastore usage percentage:
    - 0-80: Green
    - 80-90: Yellow
    - 90-100: Red
    """
    try:
        usage = float(val)
        if usage >= 90:
            return DCOreport.PASTEL_RED
        elif usage >= 80:
            return DCOreport.PASTEL_YELLOW
        return DCOreport.PASTEL_GREEN
    except:
        return ''

def color_vm_state(row):
    """
    Colors VM rows based on power state.
    """
    state = row.get("power_state", "")
    if state != "POWERED_ON":
        return [DCOreport.PASTEL_RED] * len(row)
    return [''] * len(row)

def create_DCI(dcocfg, dcorpt):
    """
    Entry point to add detailed vCenter tables to the DCI report.
    """
    for instance in dcocfg.instances(system):
        # --- 1. Datastore Status Table ---
        ds_detail = DCOreport.csv_to_styleddf(system, instance, "datastoreStatus", dcocfg)
        if not ds_detail.data.empty:
            # Apply coloring to % Used column
            ds_detail = DCOreport.apply_styler_map(ds_detail, color_datastore_usage, subset=["% Used"])
            
            # Format numbers
            ds_detail = ds_detail.format({
                "Total (TB)": "{:.2f}",
                "Free (TB)": "{:.2f}",
                "% Used": "{:.1f}%"
            })
            
            # Word wrap for hosts column (can be long)
            ds_detail = DCOreport.column_wordwrap(ds_detail, ["hosts"])
            
            dcorpt.add_table("Compute", "vSphere", instance, "Datastore Capacity Detail", ds_detail, tableset="Overview")

        # --- 2. VM Status Table ---
        vm_detail = DCOreport.csv_to_styleddf(system, instance, "vmStatus", dcocfg)
        if not vm_detail.data.empty:
            # Apply color to rows where VM is not POWERED_ON
            vm_detail = vm_detail.apply(color_vm_state, axis=1)
            
            # Column word wrap for VM names if they are long
            vm_detail = DCOreport.column_wordwrap(vm_detail, ["name"])
            
            dcorpt.add_table("Compute", "vSphere", instance, "VM Power Status Detail", vm_detail, tableset="Overview")
            
        # --- 3. Alerts Detail Table ---
        # This will contain trigged alarms from the last scan
        try:
            alerts_detail = DCOreport.csv_to_styleddf(system, instance, "alertsDetail", dcocfg)
            if not alerts_detail.data.empty:
                # Apply row coloring based on status
                def color_alerts_row(row):
                    status = str(row.get('overall_status', '')).lower()
                    if 'red' in status or 'critical' in status:
                        return [DCOreport.PASTEL_RED] * len(row)
                    elif 'yellow' in status or 'warning' in status:
                        return [DCOreport.PASTEL_YELLOW] * len(row)
                    elif 'green' in status or 'ok' in status:
                        return [DCOreport.PASTEL_GREEN] * len(row)
                    return [''] * len(row)

                alerts_detail = alerts_detail.apply(color_alerts_row, axis=1)
                
                # Column word wrap for description
                alerts_detail = DCOreport.column_wordwrap(alerts_detail, ["alarm_description"])
                
                dcorpt.add_table("Compute", "vSphere", instance, "Alerts Detail", alerts_detail, tableset="Alerts")
        except Exception as e:
            # Handle case where file might not exist yet if soap failed
            pass

if __name__ == "__main__":
    from common.DCOconfig import DCOconfig
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("vSphere DCI TEST")
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html("test_vc_dci_report.html")

