import functools
import pandas as pd
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

def colorRedNonZero(val):
    return DCOreport.PASTEL_RED if val != 0 else ''

def colorYellowNonZero(val):
    return DCOreport.PASTEL_YELLOW if val != 0 else ''

colorTempRows = functools.partial(
    DCOreport.rate_num_rows,
    column="Temp Cº",
    rate_intervals=[0, 45, 60, 100],
    rating=DCOreport.COLORS_GYR,
    force_conversion=True
)

colorBySeverityVal = functools.partial(
    DCOreport.key_color_value,
    key_color={
        "Critical": DCOreport.PASTEL_RED,
        "Major": DCOreport.PASTEL_ORANGE,
        "Warning": DCOreport.YELLOW,
        "OK": DCOreport.GREEN}
)

colorBySeverityRow = functools.partial(
    DCOreport.key_color_rows,
    column="Severity",
    key_color={"critical": DCOreport.PASTEL_RED, "warning": DCOreport.PASTEL_YELLOW}
)

def colorByStatus(row):
    return DCOreport.key_color_rows(row, "status", key_color={"up": DCOreport.GREEN}, def_color=DCOreport.PASTEL_RED)

def colorPortByExpectedStatus(row):
    color = ''
    if row['Expected Status'] == "Up" and row['Status'] == "Down":
        color = DCOreport.PASTEL_RED
    elif row['Expected Status'] == "Down" and row['Status'] == "Up":
        color = DCOreport.PASTEL_YELLOW
    elif row['Expected Status'] == "Up" and row['Status'] == "Up":
        color = DCOreport.PASTEL_GREEN
    return [color] * len(row)

def create_DCI(dcocfg, dcorpt):
    system = "OS10"

    for instance in dcocfg.instances(system):
        systemSummary = DCOreport.csv_to_styleddf(system, instance,  "systemSummary", dcocfg)
        if not systemSummary.data.empty:
            systemSummary = DCOreport.apply_styler_map(systemSummary, colorBySeverityVal)
            dcorpt.add_table("Network", "Switches", f"{instance}", "System Summary", systemSummary, tableset="Summary1")

        powersuplies = DCOreport.csv_to_styleddf(system, instance,  "powersuplies", dcocfg)
        if not powersuplies.data.empty:
            powersuplies = powersuplies.apply(colorByStatus, axis=1)
            dcorpt.add_table("Network", "Switches", f"{instance}", "Power Supplies", powersuplies, tableset="Summary2/col1")

        fans = DCOreport.csv_to_styleddf(system, instance,  "fans", dcocfg)
        if not fans.data.empty:
            fans = fans.apply(colorByStatus, axis=1)
            dcorpt.add_table("Network", "Switches", f"{instance}", "Fans", fans, tableset="Summary2/col1")

        thermal = DCOreport.csv_to_styleddf(system, instance,  "thermal", dcocfg)
        if not thermal.data.empty:
            thermal = thermal.apply(colorTempRows, axis=1)
            dcorpt.add_table("Network", "Switches", f"{instance}", "Temperatures", thermal, tableset="Summary2/col1")

        portSummary = DCOreport.csv_to_styleddf(system, instance,  "port_status", dcocfg)
        if not portSummary.data.empty:
            portSummary = portSummary.apply(colorPortByExpectedStatus, axis=1)
            dcorpt.add_table("Network", "Switches", f"{instance}", "Port Status", portSummary, tableset="Summary2")

        alertSummary = DCOreport.csv_to_styleddf(system, instance,  "alertSummary", dcocfg)
        if not alertSummary.data.empty:
            alertSummary = DCOreport.format_by_rowid(
                alertSummary,
                [("Critical", colorRedNonZero),
                ("Major", colorRedNonZero),
                ("Warning", colorYellowNonZero)]
            )
            dcorpt.add_table("Network", "Switches", f"{instance}", "Alert Summary", alertSummary, tableset="Summary1")

        alertDetail = DCOreport.csv_to_styleddf(system, instance,  "alertDetail", dcocfg)
        if not alertDetail.data.empty:
            alertDetail = DCOreport.column_wordwrap(alertDetail, ["Description"])
            alertDetail = alertDetail.apply(colorBySeverityRow, axis=1)
            dcorpt.add_table("Network", "Switches", f"{instance}", "Alerts By Severity", alertDetail, tableset="alertDetail")

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("OS10")
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html("reports/OS10reportDCI.html")
