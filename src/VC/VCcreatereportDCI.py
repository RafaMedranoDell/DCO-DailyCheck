import functools
import pandas as pd
import common.DCOreport as DCOreport

# Global variable for the system type
system = "VC"

color_datastore_usage = functools.partial(
    DCOreport.rate_num_value,
    rate_intervals=[0, 85, 95, 101],
    rating=DCOreport.COLORS_GYR,
    force_conversion=True
)

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
        # Load raw dataframe first to filter
        df_vms = dcocfg.load_csv_to_dataframe(system, instance, "vmStatus")
        if not df_vms.empty:
            # Filter to keep only VMs that are NOT POWERED_ON
            df_off_vms = df_vms[df_vms["power_state"] != "POWERED_ON"]
            
            if not df_off_vms.empty:
                # Create styled dataframe from the filtered results
                vm_detail = DCOreport.table_base_styler(df_off_vms)
                
                # Apply color to rows (they will all be colored as they are not POWERED_ON)
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

