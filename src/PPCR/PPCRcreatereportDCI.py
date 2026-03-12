import functools
import pandas as pd
import common.functions as fn
from common.DCOconfig import DCOconfig
import common.DCOreport as DCOreport




def colorAlertsBySeverityVal(val):
    color_rules = {
        "Critical": DCOreport.PASTEL_RED,
        "Warning": DCOreport.YELLOW,
        "Running": DCOreport.PASTEL_ORANGE,
        "OK": DCOreport.GREEN}
    return DCOreport.key_color_value(val, key_color=color_rules)

color_jobsByStatus = functools.partial(
    DCOreport.key_color_rows,
    column="Status",
    key_color={"Critical": DCOreport.PASTEL_RED, "Warning": DCOreport.YELLOW}
)

colorAlertBySeverityRowDeta = functools.partial(
    DCOreport.key_color_rows,
    column="Severity",
    key_color={"Critical": DCOreport.PASTEL_RED, "Warning": DCOreport.YELLOW}
)



def colorByPolicyDuration(row):
    """
    Coloring logic for Policies table:
    - Yellow: No 'Update date' ( unfinished jobs)
    - Red: Update is older than 24 hours
    - Green: Update is within last 24 hours
    """
    if row["Update date"] == "-":
        color = DCOreport.PASTEL_YELLOW
    elif row["elapsed_seconds"] >= 3600*24:
        color = DCOreport.PASTEL_RED
    else:
        color = DCOreport.PASTEL_GREEN
    return [color] * len(row)

def colorByCScapacity(val):
    return DCOreport.rate_num_value(val, [0, 80, 90, 100], DCOreport.COLORS_GYR, force_conversion=True)

def colorByCSdays(val):
    return DCOreport.rate_num_value(val, [0, 30, 90, 10000], DCOreport.COLORS_RYG, force_conversion=True)

def create_DCI(dcocfg, dcorpt):
    system = "PPCR"
    for instance in dcocfg.instances(system):
        alertDetail = DCOreport.csv_to_styleddf(system, instance, "alertDetail", dcocfg)
        if not alertDetail.data.empty:
            alertDetail = DCOreport.column_wordwrap(alertDetail, columns=['Summary', 'Remedy'])
            alertDetail = alertDetail.apply(colorAlertBySeverityRowDeta, axis=1)
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "Alert detail", alertDetail, tableset="ts2")

        df_policies = dcocfg.load_csv_to_dataframe(system, instance, "policiesDetail")
        if not df_policies.empty:
            # Re-format 'Time since last update' to ensure zero padding if using an old CSV
            if "elapsed_seconds" in df_policies.columns and "Time since last update" in df_policies.columns:
                 # Only re-format if it's not the "Check jobs" workaround
                 mask = df_policies["Time since last update"] != "Check jobs"
                 df_policies.loc[mask, "Time since last update"] = df_policies.loc[mask, "elapsed_seconds"].apply(fn.format_duration)

            policiesDetail = DCOreport.table_base_styler(df_policies)
            policiesDetail = policiesDetail.apply(colorByPolicyDuration, axis=1)
            # Hide "elapsed_seconds" column used to colorize the policies
            policiesDetail = policiesDetail.hide(['elapsed_seconds'], axis=1)
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "Policies", policiesDetail, tableset="ts3")

        df_system = dcocfg.load_csv_to_dataframe(system, instance, "systemJobs")
        if not df_system.empty:
            # Reformat 'Elapsed seconds' as requested using common function
            if "Elapsed seconds" in df_system.columns:
                df_system["Elapsed seconds"] = pd.to_numeric(df_system["Elapsed seconds"], errors='coerce').fillna(0).apply(fn.format_duration)
                df_system = df_system.rename(columns={"Elapsed seconds": "Elapsed time"})
            
            systemJobs = DCOreport.table_base_styler(df_system)
            systemJobs = DCOreport.column_wordwrap(systemJobs, columns=['Detailed description'])
            systemJobs = systemJobs.apply(color_jobsByStatus, axis=1)
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "System Jobs", systemJobs, tableset="ts4")

        df_protection = dcocfg.load_csv_to_dataframe(system, instance, "protectionJobs")
        if not df_protection.empty:
            # Reformat 'Elapsed seconds' as requested using common function
            if "Elapsed seconds" in df_protection.columns:
                df_protection["Elapsed seconds"] = pd.to_numeric(df_protection["Elapsed seconds"], errors='coerce').fillna(0).apply(fn.format_duration)
                df_protection = df_protection.rename(columns={"Elapsed seconds": "Elapsed time"})

            protectionJobs = DCOreport.table_base_styler(df_protection)
            protectionJobs = DCOreport.column_wordwrap(protectionJobs, columns=['Detailed description'])
            protectionJobs = protectionJobs.apply(color_jobsByStatus, axis=1)
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "Protection Jobs", protectionJobs, tableset="ts5")

        # Add CyberSense license information
        csCapacity = DCOreport.csv_to_styleddf(system, instance, "cs_capacity", dcocfg)
        if not csCapacity.data.empty:
            cs_instance = csCapacity.columns[1]
            csCapacity = DCOreport.format_cells_by_rowid(csCapacity, 'Used percent (%)', colorByCScapacity)
            csCapacity = DCOreport.format_nums_by_rowid(csCapacity, "Used capacity (TB)", "{:.2f}")
            csCapacity = DCOreport.format_nums_by_rowid(csCapacity, "Total capacity (TB)", "{:.2f}")
            csCapacity = DCOreport.format_nums_by_rowid(csCapacity, "Used percent (%)", "{:.2f}")
            dcorpt.add_table("Protection", "PowerProtect CyberSense", f"Instance {cs_instance}", "Capacity licensing", csCapacity, tableset="ts6")

        csLicense = DCOreport.csv_to_styleddf(system, instance, "cs_expiration", dcocfg)
        if not csLicense.data.empty:
            cs_instance = csCapacity.columns[1]
            csLicense = DCOreport.format_cells_by_rowid(csLicense, 'Remaining days', colorByCSdays)
            csLicense = DCOreport.format_nums_by_rowid(csLicense, "Remaining days", "{:,.0f}")
            dcorpt.add_table("Protection", "PowerProtect CyberSense", f"Instance {cs_instance}", "Date licensing", csLicense, tableset="ts6")

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("PowerProtect CyberRecovery")
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html("reports/PPCRreportDCI.html")
