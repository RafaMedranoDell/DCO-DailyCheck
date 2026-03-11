import functools
import logging
import common.functions as fn
from common.DCOconfig import DCOconfig
import common.DCOreport as DCOreport

boldLines = functools.partial(
    DCOreport.key_color_rows,
    column="key",
    key_color={
        'SYSTEM STATUS (ALERTS) (*)': 'font-weight: bold',
        'CAPACITY STATUS': 'font-weight: bold'}
)

colorByStatus = functools.partial(
    DCOreport.key_color_value,
    key_color={"GOOD": DCOreport.PASTEL_GREEN, "FAIR": DCOreport.PASTEL_YELLOW},
    def_color=DCOreport.PASTEL_RED
)

colorBySystemScore = functools.partial(
    DCOreport.rate_num_value,
    rate_intervals=[0, 75, 90, 100],
    rating=DCOreport.COLORS_RYG,
    force_conversion=True
)

def colorNonZeroRed(val):
    return DCOreport.PASTEL_RED if val != "0" else ''

def colorNonZeroYellow(val):
    return DCOreport.PASTEL_YELLOW if val != "0" else ''

def create_DC(dcocfg, dcorpt):
    system = "PPDM"

    # Get summarized dataframe for all the instances of this system type
    summaryDf = fn.systemSummary(system, "", "", dcocfg)
    if not summaryDf.empty:
        # Apply base style with equal width columns (fixed) to the sumarized dataframe
        summaryDfsty = DCOreport.table_base_styler(summaryDf, fixed=True)

        # Bold text for lines SYSTEM STATUS and CAPACITY STATUS
        summaryDfsty = summaryDfsty.apply(boldLines, axis=1)

        # Apply format based on row names
        summaryDfsty = DCOreport.format_by_rowid(
            summaryDfsty,
            [
                ("SystemScore", colorBySystemScore),
                ("STATUS", colorByStatus),
                ("Failed", colorNonZeroRed),
                ("Completed with Exceptions", colorNonZeroYellow),
                ("Canceled", colorNonZeroYellow),
                ("Skipped", colorNonZeroYellow),
                ("Unknown", colorNonZeroYellow)
            ]
            )

        # Add table to the report
        dcorpt.add_table("Protection", "Power Protect", "", "Data Manager", summaryDfsty)

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), "PPDMdebug", level=logging.DEBUG)
    dcorpt = DCOreport.DCOreport("DCO Daily Check report")
    create_DC(dcocfg, dcorpt)
    dcorpt.save_html("reports/PPDMreportDC.html")
