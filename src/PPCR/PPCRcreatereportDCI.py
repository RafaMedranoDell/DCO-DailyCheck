import functools
import pandas as pd
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
    color = DCOreport.GREEN if row["elapsed_seconds"] < 3600*24 else DCOreport.PASTEL_YELLOW
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

        policiesDetail = DCOreport.csv_to_styleddf(system, instance, "policiesDetail", dcocfg)
        if not policiesDetail.data.empty:
            policiesDetail = policiesDetail.apply(colorByPolicyDuration, axis=1)
            # Hide "elapsed_seconds" column used to colorize the policies
            policiesDetail = policiesDetail.hide(['elapsed_seconds'], axis=1)
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "Policies", policiesDetail, tableset="ts3")

        systemJobs = DCOreport.csv_to_styleddf(system, instance, "systemJobs", dcocfg)
        if not systemJobs.data.empty:
            systemJobs = DCOreport.column_wordwrap(systemJobs, columns=['Detailed description'])
            systemJobs = systemJobs.apply(color_jobsByStatus, axis=1)
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "System Jobs", systemJobs, tableset="ts4")

        protectionJobs = DCOreport.csv_to_styleddf(system, instance, "protectionJobs", dcocfg)
        if not protectionJobs.data.empty:
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
