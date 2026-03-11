import functools
import logging
import pandas as pd
import common.functions as fn
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig




def color_alertsDetail(row):
    if row['Severity'] in ['EMERGENCY', 'ALERT', 'CRITICAL','ERROR']:
        return [DCOreport.PASTEL_RED] * len(row)
    elif row['Severity'] in ['WARNING', 'NOTICE', 'INFO', 'DEBUG']:
        return [DCOreport.PASTEL_YELLOW] * len(row)



def color_replicasStatus_sync(row):
    return DCOreport.rate_num_rows(
        row,
        'secondsSinceLastSync',
        rate_intervals=[0, 25*3600, 49*3600, 4*365*24*3600],
        rating=DCOreport.COLORS_GYR,
        force_conversion=True)

def color_tiersStatus_percent(val):
    return DCOreport.rate_num_value(
        val,
        rate_intervals=[0, 80, 90, 100],
        rating=DCOreport.COLORS_GYR,
        force_conversion=True)

def create_DCI(dcocfg, dcorpt):
    system = "DD"
    for instance in dcocfg.instances(system):
        # --- TABLAS EN PARALELO (ts1) ---

        # 1. TIER STATUS (Columna 1)
        tiersStatus = DCOreport.csv_to_styleddf(system, instance,  "tiersStatus", dcocfg)
        if not tiersStatus.data.empty:
            tiersStatus = DCOreport.apply_styler_map(tiersStatus, color_tiersStatus_percent, subset=["% Used"])
            tiersStatus = tiersStatus.format({
                "% Used": "{:.1f}",
                "Total (TB)": "{:.2f}",
                "Used (TB)": "{:.2f}",
                "Available (TB)": "{:.2f}"
            })
            dcorpt.add_table("Protection", "Data Domain", f"{instance}", "Tier Status", tiersStatus, tableset="ts1/col1")

        # 2. REPLICATION STATUS (Columna 2)
        replicasStatus = DCOreport.csv_to_styleddf(system, instance,  "replicasStatus", dcocfg)
        if not replicasStatus.data.empty:
            replicasStatus = replicasStatus.apply(color_replicasStatus_sync, axis=1)
            # Hide "elapsed_seconds" column used to colorize the policies
            replicasStatus = replicasStatus.hide(['secondsSinceLastSync'], axis=1)
            # Título actualizado a "Replication Status"
            dcorpt.add_table("Protection", "Data Domain", f"{instance}", "Replication Status", replicasStatus, tableset="ts1/col2")

        # --- TABLA INFERIOR (ts2) ---

        # 3. ALERTS DETAIL (Ocupa todo el ancho debajo)
        alertsDetail = DCOreport.csv_to_styleddf(system, instance,  "alertsDetail", dcocfg)
        if not alertsDetail.data.empty:
            alertsDetail = DCOreport.column_wordwrap(alertsDetail, ["Description", "Message"])
            alertsDetail = alertsDetail.apply(color_alertsDetail, axis=1)
            dcorpt.add_table("Protection", "Data Domain", f"{instance}", "Alerts Detail", alertsDetail, tableset="ts2")

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), "DDdebug", level=logging.DEBUG)
    dcorpt = DCOreport.DCOreport("Data Domain")
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html("reports/DDreportDCI.html")
