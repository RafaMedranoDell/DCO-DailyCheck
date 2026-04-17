import common.functions as fn
import pandas as pd
import functools
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "IDRAC"

color_alertsBySeverityVal = functools.partial(
    DCOreport.key_color_value,
    key_color={
        "Critical": DCOreport.PASTEL_RED,
        "Warning": DCOreport.PASTEL_ORANGE,
        "Unknown": DCOreport.YELLOW,
        "OK": DCOreport.GREEN})

def create_DC(dcocfg, dcorpt):
    # Get summarized dataframe for all the instances of this system type
    summaryDf = fn.systemSummary(system, "System Name", "systemSummary", dcocfg)
    if not summaryDf.empty:
        # Apply base style with equal width columns (fixed) to the sumarized dataframe
        summaryDfsty = DCOreport.table_base_styler(summaryDf, fixed=True)

        # Colorize the data columns based on the status
        for instance in summaryDfsty.data.columns:
            summaryDfsty = summaryDfsty.map(color_alertsBySeverityVal, subset=[instance])

        # Add table to the report under 'Compute' section
        dcorpt.add_table("Compute", "IDRAC Servers", "", "", summaryDfsty)

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport(f'DCO Daily Check report for {system}')
    create_DC(dcocfg, dcorpt)
    dcorpt.save_html(f'reports/{system}reportDC.html')
