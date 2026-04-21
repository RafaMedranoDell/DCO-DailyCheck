import functools
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable for the system type
system = "ESX"

color_datastore_usage = functools.partial(
    DCOreport.rate_num_value,
    rate_intervals=[0, 85, 95, 101],
    rating=DCOreport.COLORS_GYR,
    force_conversion=True
)


def color_vm_state(row):
    """Colors VM rows based on power state (non-poweredOn = red)."""
    state = row.get("power_state", "")
    if state != "poweredOn":
        return [DCOreport.PASTEL_RED] * len(row)
    return [''] * len(row)


def create_DCI(dcocfg, dcorpt):
    """
    Entry point to add detailed ESX standalone tables to the DCI report.
    """
    for instance in dcocfg.instances(system):
        full_name = dcocfg.get_instance_full_name(system, instance)

        # --- 1. Datastore Capacity Detail ---
        ds_detail = DCOreport.csv_to_styleddf(system, instance, "datastoreStatus", dcocfg)
        if not ds_detail.data.empty:
            ds_detail = DCOreport.apply_styler_map(ds_detail, color_datastore_usage, subset=["% Used"])
            ds_detail = ds_detail.format({
                "Total (TB)": "{:.2f}",
                "Free (TB)":  "{:.2f}",
                "% Used":     "{:.1f}%"
            })
            dcorpt.add_table("Compute", "ESX", full_name, "Datastore Capacity Detail", ds_detail, tableset="Overview")

        # --- 2. VM Power Status Detail ---
        df_vms = dcocfg.load_csv_to_dataframe(system, instance, "vmStatus")
        if not df_vms.empty:
            for col in ["name", "power_state"]:
                if col not in df_vms.columns:
                    df_vms[col] = "UNKNOWN"
            df_off_vms = df_vms[df_vms["power_state"] != "poweredOn"]
            if not df_off_vms.empty:
                vm_detail = DCOreport.table_base_styler(df_off_vms)
                vm_detail = vm_detail.apply(color_vm_state, axis=1)
                vm_detail = DCOreport.column_wordwrap(vm_detail, ["name"])
                dcorpt.add_table("Compute", "ESX", full_name, "VM Power Status Detail", vm_detail, tableset="Overview")

        # --- 3. Alerts Detail ---
        try:
            alerts_detail = DCOreport.csv_to_styleddf(system, instance, "alertsDetail", dcocfg)
            if not alerts_detail.data.empty:
                def color_alerts_row(row):
                    status = str(row.get("overall_status", "")).lower()
                    if "red" in status or "critical" in status:
                        return [DCOreport.PASTEL_RED] * len(row)
                    elif "yellow" in status or "warning" in status:
                        return [DCOreport.PASTEL_YELLOW] * len(row)
                    elif "green" in status or "ok" in status:
                        return [DCOreport.PASTEL_GREEN] * len(row)
                    return [''] * len(row)

                alerts_detail = alerts_detail.apply(color_alerts_row, axis=1)
                alerts_detail = DCOreport.column_wordwrap(alerts_detail, ["alarm_description"])
                dcorpt.add_table("Compute", "ESX", full_name, "Alerts Detail", alerts_detail, tableset="Alerts")
        except Exception:
            pass


if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("ESX Standalone DCI TEST")
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html("test_esx_dci_report.html")
