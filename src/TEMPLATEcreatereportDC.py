import common.functions as fn
import pandas as pd
import functools
import common.functions as fn
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "product"

# Configure module logger
logger = fn.get_module_logger(__name__)

color_alertsBySeverityVal = functools.partial(
    DCOreport.key_color_value,
    key_color={
        "Critical": DCOreport.PASTEL_RED,
        "Major": DCOreport.PASTEL_ORANGE,
        "Warning": DCOreport.YELLOW,
        "OK": DCOreport.GREEN})

def create_DC(dcocfg, dcorpt):
    logger.info(f'Generating DC for {system} systems')

    # Get summarized dataframe for all the instances of this system type
    summaryDf = fn.systemSummary(system, "<firstColumnTitle>", "systemSummary", dcocfg)
    if not summaryDf.empty:
        # Apply base style with equal width columns (fixed) to the sumarized dataframe
        summaryDfsty = DCOreport.table_base_styler(summaryDf, fixed=True)

        # Apply format based on row names
        summaryDfsty = DCOreport.format_by_rowid(
            summaryDfsty,
            [
                ("row1", colorByStatus),
                ("row2", formatFunction2),
                ("row3", formatFunction3),
                ("row4", formatFunction4)
            ]
        )
        # Add table to the report
        dcorpt.add_table("<subsystem>", "<family>", "<product>", "Summary", summaryDfsty)

        # If all the rows use the same function we can colorize complete columns
        # # Colorize the data columns based on the status
        # for instance in summaryDf.data.columns:
        #     summaryDfsty = DCOreport.apply_styler_map(summaryDfsty, color_alertsBySeverityVal, subset=[instance])
        #
        # # Add table to the report
        # dcorpt.add_table("<subsystem>", "<family>", "<product>", "Summary", summaryDfsty)

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport(f'DCO Daily Check report for {system}')
    create_DC(dcocfg, dcorpt)
    dcorpt.save_html(f'reports/{system}reportDC.html')
