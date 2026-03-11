import common.functions as fn
import pandas as pd
import functools
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

color_alertsBySeverityVal = functools.partial(
    DCOreport.key_color_value,
    key_color={
        "Critical": DCOreport.PASTEL_RED,
        "Major": DCOreport.PASTEL_ORANGE,
        "Warning": DCOreport.YELLOW,
        "OK": DCOreport.GREEN})

def create_DC(dcocfg, dcorpt):
    system = "OS10"

    # Get summarized dataframe for all the instances of this system type
    summaryDf = fn.systemSummary(system, "TOR", "systemSummary", dcocfg)
    if not summaryDf.empty:
        # Apply base style with equal width columns (fixed) to the sumarized dataframe
        summaryDfsty = DCOreport.table_base_styler(summaryDf, fixed=True)

        # Colorize the data columns based on the status
        for instance in summaryDfsty.data.columns:
            summaryDfsty = DCOreport.apply_styler_map(summaryDfsty, color_alertsBySeverityVal, subset=[instance])

        # Add table to the report
        dcorpt.add_table("Network", "", "", "Switches", summaryDfsty)

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("DCO Daily Check report")
    create_DC(dcocfg, dcorpt)
    dcorpt.save_html("reports/OS10reportDC.html")
