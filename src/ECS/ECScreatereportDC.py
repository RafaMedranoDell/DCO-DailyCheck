import common.functions as fn
import os
import functools
import pandas as pd
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

boldLines = functools.partial(
    DCOreport.key_color_rows,
    column="ECS",
    key_color={
        'NODES STATUS': 'font-weight: bold',
        'DISKS STATUS': 'font-weight: bold',
        'ALERTS': 'font-weight: bold',
        'CAPACITY STATUS': 'font-weight: bold'}
)

def colorStatusIntelligent(val):
    """
    Coloring based on keywords in the status text.
    """
    val_str = str(val)
    if "Error" in val_str or "Critical" in val_str:
        return DCOreport.PASTEL_RED
    if "Warning" in val_str:
        return DCOreport.PASTEL_YELLOW
    if "Info" in val_str:
        return DCOreport.PASTEL_BLUE  # Pastel Blue for Info
    if "OK" in val_str:
        return DCOreport.PASTEL_GREEN
    return ''

colorByPercent = functools.partial(
    DCOreport.rate_num_value,
    rate_intervals=[0, 70, 85, 100],
    rating=DCOreport.COLORS_GYR,
    force_conversion=True
)

def create_DC(dcocfg, dcorpt):
    system = "ECS"

    # Get summarized dataframe for all the instances of this system type
    summaryDf = fn.systemSummary(system, "ECS", "systemSummary", dcocfg)
    if not summaryDf.empty:
        # Apply base style with equal width columns (fixed) to the sumarized dataframe
        summaryDfsty = DCOreport.table_base_styler(summaryDf, fixed=True)

        # Apply format based on row names
        summaryDfsty = DCOreport.format_by_rowid(
            summaryDfsty,
            [
                ("Nodes Status", colorStatusIntelligent),
                ("Disks Status", colorStatusIntelligent),
                ("Alerts Status", colorStatusIntelligent),
                ("Storage Utilization (%)", colorByPercent)
            ]
        )

        # Format utilization with decimals
        summaryDfsty = DCOreport.format_nums_by_rowid(summaryDfsty, "Storage Utilization (%)", "{:.2f}%")

        # Add table to the report
        dcorpt.add_table("Storage", "ECS", "", "", summaryDfsty)

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("DCO Daily Check report")
    create_DC(dcocfg, dcorpt)
    dcorpt.save_html("reports/ECSreportDC.html")
